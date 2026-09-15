from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401 # create_all でテーブル定義を参照する際に必要
from app.api import chat
from app.db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(chat.router)
app.frontend("/", directory="public")
