from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    bigquery_project_id: str
    bigquery_location: str
    gemini_project_id: str
    gemini_location: str
    gemini_model: str


settings = Settings()
