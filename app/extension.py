from dotenv import load_dotenv
import os

load_dotenv()
from fastapi.security import OAuth2PasswordBearer

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from app.database import init_db, AsyncSessionLocal

import logging

logging.getLogger("urllib3").setLevel(logging.CRITICAL)


origins = ["*"]

app = FastAPI(
    docs_url="/docs",
    title="Mini Etherscan ***" + os.getenv("ENV") + "***",
    summary="API para consultas de rede ethereum",
    openapi_url="/openapi.json",
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token", auto_error=False
)  # Sua rota de autenticação

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Criar as tabelas no banco de dados (caso não existam)
# Base.metadata.create_all(bind=engine)


@app.on_event("startup")
async def startup_event():
    await init_db()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@app.on_event("shutdown")
async def shutdown():
    pass
    # await app.state.db.close()
