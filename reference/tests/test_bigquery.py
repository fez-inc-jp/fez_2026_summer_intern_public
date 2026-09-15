from datetime import date, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from google.cloud.bigquery import Row, SchemaField

from app.integrations import bigquery as bq

disallowed_query_params = pytest.mark.parametrize(
    "statement_type, total_bytes",
    [["SELECT", bq._BQ_MAX_BYTES + 1], ["CREATE_TABLE", 1], ["DELETE", 1]],
)


# BigQuery のデータ型と Python のデータ型の対応表: https://docs.cloud.google.com/bigquery/docs/dataframes-data-types?hl=ja#type-mappings
def test_convert_to_json_type():
    """JSON に適したデータ型の変換が行われている"""
    none = None
    assert bq._convert_to_json_type(none) is None

    bool_value = True
    assert type(bq._convert_to_json_type(bool_value)) is bool

    str_value = "str"
    assert type(bq._convert_to_json_type(str_value)) is str

    int_value = 123
    assert type(bq._convert_to_json_type(int_value)) is int

    float_value = 123.45
    assert type(bq._convert_to_json_type(float_value)) is float

    decimal_value = Decimal(100_000)
    assert type(bq._convert_to_json_type(decimal_value)) is float

    date_value = date(2026, 6, 1)
    assert bq._convert_to_json_type(date_value) == "2026-06-01"

    datetime_value = datetime(2026, 6, 1, 12, 1, 1)
    assert bq._convert_to_json_type(datetime_value) == "2026-06-01T12:01:01"

    time_value = time(12, 1, 1)
    assert bq._convert_to_json_type(time_value) == "12:01:01"

    timestamp_value = datetime(2026, 6, 1, 12, 1, 1, tzinfo=ZoneInfo(key="Asia/Tokyo"))
    assert bq._convert_to_json_type(timestamp_value) == "2026-06-01T12:01:01+09:00"

    # list は定義されてないので str で返す
    list_value = ["a", "b", "c"]
    assert type(bq._convert_to_json_type(list_value)) is str

    # dict は定義されてないので str で返す
    dict_value = {"a": 1, "b": 2, "c": 3}
    assert type(bq._convert_to_json_type(dict_value)) is str


@disallowed_query_params
def test_guard_disallowed_query(statement_type, total_bytes):
    """許可されていないクエリで例外を返す"""
    with pytest.raises(bq.QueryNotAllowedError):
        bq._guard(statement_type=statement_type, total_bytes=total_bytes)


def test_not_guard_allowed_query():
    """許可されているクエリは例外を返さない"""
    bq._guard(statement_type="SELECT", total_bytes=1)
    bq._guard(statement_type="SELECT", total_bytes=bq._BQ_MAX_BYTES)


def test_build_result():
    schema = [
        SchemaField("usage_date", "DATE"),
        SchemaField("average_minutes", "NUMERIC"),
    ]
    rows = [
        Row((date(2026, 6, 1), Decimal("36.17")), {"usage_date": 0, "average_minutes": 1}),
        Row((date(2026, 6, 2), Decimal("26.2")), {"usage_date": 0, "average_minutes": 1}),
    ]
    assert bq._build_result(schema, rows) == {
        "columns": ["usage_date", "average_minutes"],
        "rows": [
            ["2026-06-01", 36.17],
            ["2026-06-02", 26.2],
        ],
    }


@disallowed_query_params
def test_disallowed_query_never_reaches_run_query(
    monkeypatch, statement_type, total_bytes
):
    """get_result に許可されていないクエリを入力してもエラーになる"""
    # BigQuery の認証が必要な部分はモックに置き換える
    monkeypatch.setattr(bq, "_get_client", lambda: object())
    monkeypatch.setattr(
        bq,
        "_dry_run",
        lambda client, query: SimpleNamespace(
            statement_type=statement_type, total_bytes_processed=total_bytes
        ),
    )

    def _must_not_run(client, query):
        raise AssertionError("許可されていないクエリが実行されました")

    monkeypatch.setattr(bq, "_run_query", _must_not_run)

    with pytest.raises(bq.QueryNotAllowedError):
        bq.get_result("dummy query")
