from datetime import date, datetime, time
from decimal import Decimal
from functools import cache

from google.cloud import bigquery

from app.config import settings
from app.schemas import chat

_BQ_MAX_BYTES = 1_000_000_000  # 1 GB
_BQ_MAX_ROWS = 1_000


class BigQueryExecutionError(Exception):
    """BigQuery API の呼び出しに失敗したことを表す例外"""


class QueryNotAllowedError(Exception):
    """許可されないクエリであることを表す例外"""


@cache
def _get_client() -> bigquery.Client:
    return bigquery.Client(
        project=settings.bigquery_project_id,
        location=settings.bigquery_location,
    )


def _dry_run(client: bigquery.Client, query: str) -> bigquery.QueryJob:
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    return client.query(query, job_config=job_config)


def _run_query(client: bigquery.Client, query: str) -> bigquery.QueryJob:
    job_config = bigquery.QueryJobConfig(maximum_bytes_billed=_BQ_MAX_BYTES)
    return client.query(query, job_config=job_config)


def _convert_to_json_type(value: object) -> chat.Cell:
    """BQ の値を JSON セーフなセル値へ変換

    JSON ネイティブ型 (str / int / float / bool / None) はそのまま通す
    NUMERIC は数値として扱えるよう float、日付・時刻系は ISO 8601 文字列へ変換する
    それ以外は最終手段として str 化し、JSONB 保存での失敗を防ぐ
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    return str(value)


def _guard(statement_type: str, total_bytes: int | None) -> None:
    """許可されないクエリを検知

    以下の場合に例外を発生させる
    - SELECT 以外のステートメントが使われている
    - スキャン量が _BQ_MAX_BYTES を超える
    """
    if statement_type != "SELECT":
        raise QueryNotAllowedError(
            f"SELECT 以外は許可されていません (statement_type={statement_type})"
        )
    if total_bytes is not None and total_bytes > _BQ_MAX_BYTES:
        raise QueryNotAllowedError(
            f"スキャン量が上限を超えています ({total_bytes} > {_BQ_MAX_BYTES})"
        )


def _build_result(schema: list[bigquery.SchemaField], rows: list[bigquery.Row]) -> dict:
    """BQ のジョブ結果を JSON 化できる形式の dict に変換する"""
    columns = [field.name for field in schema]
    rows = [[_convert_to_json_type(v) for v in row.values()] for row in rows]
    return {"columns": columns, "rows": rows}


def get_result(query: str) -> dict:
    """BQ へクエリを発行し結果を取得

    columns と rows の 2 要素をもち、各セル値を JSON 化できる形に変換済みの dict を返す
    """
    try:
        client = _get_client()
        dry_run_job = _dry_run(client, query)
    except Exception as exc:
        raise BigQueryExecutionError(str(exc)) from exc

    _guard(dry_run_job.statement_type, dry_run_job.total_bytes_processed)

    try:
        job = _run_query(client, query)
        result = job.result(max_results=_BQ_MAX_ROWS)
        rows = list(result)
    except Exception as exc:
        raise BigQueryExecutionError(str(exc)) from exc

    return _build_result(result.schema, rows)
