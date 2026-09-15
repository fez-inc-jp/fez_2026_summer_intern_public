"""chat API の I/O スキーマ

フロントエンドと取り交わす JSON の形 (API 契約) を定義する
DB での保持形式 (app/models/chat.py) とは独立で、両者の変換は api 層が担う

いずれも table=True を持たない SQLModel であり、純粋なデータモデルとして働く
クラス名は SQLModel 公式の命名慣行 (Public / Create / Update) に従う
"""

from uuid import UUID

from sqlmodel import SQLModel

# テーブルセルが取りうる値の型
Cell = str | int | float | bool | None


class ChatResult(SQLModel):
    """自然言語クエリから得たテーブル結果"""

    columns: list[str]  # カラム名の配列
    rows: list[list[Cell]]  # 各行はカラム数長の配列
    summary: str  # テーブルのサマリ文章
    sql: str  # データ出力に使った SQL 文章


class ChatPublic(SQLModel):
    """1 件の完全な chat (GET 単体 / POST / PUT のレスポンス)"""

    id: UUID
    title: str  # チャットのタイトル
    prompt: str  # はじめのプロンプト
    result: ChatResult


class ChatSummary(SQLModel):
    """一覧用の軽量サマリ (result を含まない)"""

    id: UUID
    title: str
    prompt: str


class ChatCreate(SQLModel):
    """POST 入力 (title / result はサーバ側で生成する想定)"""

    prompt: str


class ChatUpdate(SQLModel):
    """PUT 入力 (更新対象は title のみ)"""

    title: str
