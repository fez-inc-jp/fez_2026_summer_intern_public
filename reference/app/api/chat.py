"""chat API (CRUD)

チャットの作成・取得・更新・削除を提供する HTTP エンドポイント群
本モジュールは HTTP の入出力・永続化・レスポンス整形を担い、
分析ロジック (SQL 生成・実行・要約) は services 層に委譲する
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Chat
from app.schemas.chat import (
    ChatCreate,
    ChatPublic,
    ChatResult,
    ChatSummary,
    ChatUpdate,
)
from app.services import analysis as service

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _to_public(chat: Chat) -> ChatPublic:
    """Chat モデルを API レスポンス用の ChatPublic に変換

    DB でフラットに保持している sql / summary / result_table を、
    API 契約の入れ子構造 (ChatResult) に組み立て直す
    """
    chat_result = ChatResult(
        columns=chat.result_table["columns"],
        rows=chat.result_table["rows"],
        summary=chat.summary,
        sql=chat.sql,
    )
    chat_public = ChatPublic(
        id=chat.id,
        title=chat.title,
        prompt=chat.prompt,
        result=chat_result,
    )
    return chat_public


def _to_summary(chat: Chat) -> ChatSummary:
    """Chat モデルを一覧用の ChatSummary に変換 (result を含まない)"""
    return ChatSummary(
        id=chat.id,
        title=chat.title,
        prompt=chat.prompt,
    )


@router.get("")
def list_chats(session: Session = Depends(get_session)) -> list[ChatSummary]:
    """chat の一覧を全件取得

    作成日時の新しい順に、result を含まない軽量なサマリを返す
    """
    chats = session.exec(select(Chat).order_by(Chat.created_at.desc()))
    return [_to_summary(chat) for chat in chats]


@router.get("/{chat_id}")
def get_chat(chat_id: UUID, session: Session = Depends(get_session)) -> ChatPublic:
    """特定の chat を 1 件取得

    表・要約・SQL を含む完全な chat を返す
    存在しない id の場合は 404 を返す
    """
    chat = session.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return _to_public(chat)


@router.post("", status_code=201)
def create_chat(
    payload: ChatCreate, session: Session = Depends(get_session)
) -> ChatPublic:
    """chat を新規作成

    prompt から分析 (タイトル生成・SQL 生成・実行・要約) を行い、
    結果を保存して作成された chat を返す

    - `201 Created`
      - 成功時
    - `422 Unprocessable Content`
      - 質問に必要な情報がなく LLM が SQL の生成を拒否した場合
        `detail.code` に `SQL_GENERATION_DECLINED`、
        `detail.message` に拒否理由を含む
      - FastAPI の入力検証エラーとは `detail.code` で区別する
      - この場合、BigQuery の実行や chat の保存は行わない
    - `500 Internal Server Error`
      - LLM・BigQuery・DB などで予期しない失敗が発生した場合
        内部の例外情報はクライアントへ公開しない
    """
    try:
        chat: Chat = service.create_chat(payload.prompt)
    except service.SQLGenerationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SQL_GENERATION_DECLINED",
                "message": str(exc),
            },
        ) from exc

    session.add(chat)
    session.commit()
    session.refresh(chat)

    return _to_public(chat)


@router.put("/{chat_id}")
def update_chat(
    chat_id: UUID, payload: ChatUpdate, session: Session = Depends(get_session)
) -> ChatPublic:
    """特定の chat の title を更新

    title 以外のフィールドは変更しない
    存在しない id の場合は 404 を返す
    """
    chat = session.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat.title = payload.title
    session.commit()
    session.refresh(chat)
    return _to_public(chat)


@router.delete("/{chat_id}", status_code=204)
def delete_chat(chat_id: UUID, session: Session = Depends(get_session)) -> None:
    """特定の chat を 1 件削除

    存在しない id に対しても 204 を返す (冪等)
    削除済みか元々無かったかをクライアントが区別しない前提の仕様
    """
    chat = session.get(Chat, chat_id)
    if chat is None:
        return
    session.delete(chat)
    session.commit()
