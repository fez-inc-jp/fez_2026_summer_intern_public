from functools import cache

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings


class LLMExecutionError(Exception):
    """LLM API の呼び出しに失敗したことを表す例外"""


class LLMResponseError(Exception):
    """LLM の応答が期待する形式に変換できなかったことを表す例外"""


@cache
def _get_client() -> genai.Client:
    return genai.Client(
        enterprise=True,
        project=settings.gemini_project_id,
        location=settings.gemini_location,
        http_options=types.HttpOptions(
            api_version="v1",
            timeout=30000,
        ),
    )


def generate_content[T: BaseModel](contents: str, response_schema: type[T]) -> T:
    """Gemini へ問合せをし、指定した形式の回答を取得"""
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
    except Exception as exc:
        raise LLMExecutionError(str(exc)) from exc

    parsed = response.parsed

    if not isinstance(parsed, response_schema):
        raise LLMResponseError("LLM の応答を期待する形式に変換できませんでした")
    return parsed
