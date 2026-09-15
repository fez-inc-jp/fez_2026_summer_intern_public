from copy import deepcopy

import pytest

from app.services import analysis


def test_build_llm_table_payload_keeps_small_table():
    """小さいテーブルはそのまま維持される"""
    table = {
        "columns": ["value"],
        "rows": [
            ["a"],
            ["b"],
            ["c"],
        ],
    }

    original = deepcopy(table)
    llm_table = analysis._build_llm_table_payload(table)

    # 元のテーブルに変更が加えられていないこと
    assert table == original

    # 出力が期待どおりであること
    assert llm_table["columns"] == table["columns"]
    assert llm_table["rows"] == table["rows"]
    assert llm_table["total_row_count"] == 3
    assert llm_table["sampled_row_count"] == 3
    assert llm_table["truncated"] is False


def test_build_llm_table_payload_handles_empty_table():
    """空テーブルでも正常に処理する"""
    table = {
        "columns": [],
        "rows": [],
    }

    original = deepcopy(table)
    llm_table = analysis._build_llm_table_payload(table)

    # 元のテーブルに変更が加えられていないこと
    assert table == original

    # 出力が期待どおりであること
    assert llm_table["columns"] == table["columns"]
    assert llm_table["rows"] == table["rows"]
    assert llm_table["total_row_count"] == 0
    assert llm_table["sampled_row_count"] == 0
    assert llm_table["truncated"] is False


def test_build_llm_table_payload_limits_rows():
    """行が 100 行を超えるときは先頭 100 行を中身を変更せずに返す"""
    table = {
        "columns": ["value"],
        "rows": [[i] for i in range(101)],
    }

    original = deepcopy(table)
    llm_table = analysis._build_llm_table_payload(table)

    # 元のテーブルに変更が加えられていないこと
    assert table == original

    # 出力が期待どおりであること
    assert llm_table["columns"] == table["columns"]
    assert llm_table["rows"] == table["rows"][:100]
    assert llm_table["total_row_count"] == 101
    assert llm_table["sampled_row_count"] == 100
    assert llm_table["truncated"] is True


def test_build_llm_table_payload_limits_characters_at_row_boundary():
    """文字数がトータル 20,000 字を超える場合はテーブルデータを制限する"""
    table = {
        "columns": ["value"],
        "rows": [
            ["a" * 9_000],
            ["b" * 9_000],
            ["c" * 9_000],
        ],
    }

    original = deepcopy(table)
    llm_table = analysis._build_llm_table_payload(table)

    # 元のテーブルに変更が加えられていないこと
    assert table == original

    # 出力が期待どおりであること
    assert llm_table["columns"] == table["columns"]
    assert llm_table["rows"] == table["rows"][:2]
    assert llm_table["total_row_count"] == 3
    assert llm_table["sampled_row_count"] == 2
    assert llm_table["truncated"] is True


def test_create_chat_stops_when_sql_generation_is_declined(monkeypatch):
    """LLM が SQL の生成を拒否したら BigQuery を呼ぶ前に例外を送る"""
    reason = "参照可能なデータではありません"

    def _generate_content(contents, response_schema):
        assert response_schema is analysis.GeneratedSQL

        return analysis.GeneratedSQL(
            result=analysis.SQLDeclined(
                status="declined",
                reason=reason,
            )
        )

    def _must_not_query(sql):
        raise AssertionError("生成拒否後に BigQuery が呼ばれました")

    monkeypatch.setattr(analysis, "generate_content", _generate_content)
    monkeypatch.setattr(analysis, "_get_table", _must_not_query)

    with pytest.raises(analysis.SQLGenerationError) as exc_info:
        analysis.create_chat("今日の天気は？")

    assert str(exc_info.value) == reason
