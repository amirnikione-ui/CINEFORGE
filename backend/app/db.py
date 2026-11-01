"""SQLAlchemy 2 async engine/session. SQLite dev default (WAL), Postgres in compose."""
from __future__ import annotations

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import DATABASE_URL

_url = DATABASE_URL
# async engine needs an async driver; auto-upgrade plain sqlite:// URLs
if _url.startswith("sqlite:///") and "+aiosqlite" not in _url:
    _url = _url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
if _url.startswith("sqlite+aiosqlite:///./"):
    # resolve relative to backend/ cwd for stable CLI usage
    import pathlib

    rel = _url.removeprefix("sqlite+aiosqlite:///")
    _url = "sqlite+aiosqlite:///" + str(pathlib.Path(rel).resolve())

_is_sqlite = "sqlite" in _url
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
engine = create_async_engine(_url, echo=False, future=True, connect_args=_connect_args)

if _is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_wal(dbapi_conn, _record):  # pragma: no cover - driver hook
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    from .models import Base

    async with engine.begin() as conn:
        if _url.startswith("postgres"):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.run_sync(Base.metadata.create_all)

async def dispose() -> None:
    await engine.dispose()
