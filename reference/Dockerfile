FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.27 /uv /uvx /bin/

COPY . /app

WORKDIR /app
RUN uv sync --frozen --no-cache

CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0"]
