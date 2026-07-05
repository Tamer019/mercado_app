import asyncpg
import os
from contextlib import asynccontextmanager

_pool = None

async def init_pool():
    global _pool
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        _pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    else:
        _pool = await asyncpg.create_pool(
            host="localhost",
            port=5433,
            database="mercadoDB",
            user="tamer",
            min_size=2,
            max_size=10,
        )

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()

@asynccontextmanager
async def get_db():
    async with _pool.acquire() as conn:
        yield conn
