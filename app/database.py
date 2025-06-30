from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./sandwiches_attacks.db"

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # evita expirar objetos após commit
)

Base = declarative_base()


async def init_db() -> None:
    """
    Executa CREATE TABLE IF NOT EXISTS para todos os modelos.
    Chamar em @app.on_event("startup").
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def restart_db() -> None:
    """
    Reinicia o banco de dados, removendo todas as tabelas e recriando-as.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
