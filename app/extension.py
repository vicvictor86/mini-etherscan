import os
from dotenv import load_dotenv

load_dotenv()
from fastapi.security import OAuth2PasswordBearer

# from app.database import Base, engine, SessionLocal

# Importar todos os modelos para garantir que sejam reconhecidos pelo SQLAlchemy
# from app.dbo import *

# from app.dbo.user_dbo import get_user
# from app.utils.functions import get_password_hash

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

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


# @app.on_event("startup")
# def startup_event():
#     # Inserir valores iniciais na tabela config, se não existirem
#     db = SessionLocal()  # Criar uma nova sessão manualmente

#     # Inserir usuário padrão, se não existir
#     if not get_user("admin", db):
#         admin_user = UserDBO(
#             username="admin",
#             full_name="Admin",
#             email="admin@admin",
#             hashed_password=get_password_hash("123admin"),
#             disabled=False,
#             role="admin",
#         )
#         db.add(admin_user)
#         db.commit()
