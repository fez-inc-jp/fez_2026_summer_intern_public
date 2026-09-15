"""chat のテーブルモデル

DB (PostgreSQL) での永続化形式を定義する。API の I/O 形式
(app/schemas/chat.py) とは独立で、両者の変換は api 層が担う

テーブルは起動時に SQLModel.metadata.create_all で作成される
create_all は既存テーブルを変更しないため、モデル定義を変えた場合は
テーブルの作り直しが必要 (マイグレーションは後続タスクで導入)
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class Chat(SQLModel, table=True):
    """チャットテーブル

    チャットの入力内容とその分析結果を保持

    分析結果は 3 点セット (SQL / 要約 / 表データ) で保持する
    sql と summary は NOT NULL 制約で必須性を保証するため独立カラムとし、
    クエリごとに構造が変わる表データのみ result_table (JSONB) に持つ
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    prompt: str
    sql: str
    result_table: dict = Field(
        sa_type=JSONB
    )  # {"columns": [...], "rows": [...]} の形で表データを保持
    summary: str
    created_at: datetime = Field(
        default_factory=utcnow, sa_type=DateTime(timezone=True), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"onupdate": utcnow},
    )
