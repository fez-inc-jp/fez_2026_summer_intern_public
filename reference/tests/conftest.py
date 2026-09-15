import os

# app.config は import 時に必須 env を要求するため、テスト収集前にダミー値を用意する
# 将来 GitHub Actions などで pytest を実行する際などに直接実行できるようにするため
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BIGQUERY_PROJECT_ID", "test-project")
os.environ.setdefault("BIGQUERY_LOCATION", "US")
os.environ.setdefault("GEMINI_PROJECT_ID", "test-project")
os.environ.setdefault("GEMINI_LOCATION", "global")
os.environ.setdefault("GEMINI_MODEL", "test-model")
