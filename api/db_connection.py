import asyncpg
import os

async def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return await asyncpg.connect(database_url)
    return await asyncpg.connect(
        host="localhost",
        port=5433,
        database="mercadoDB",
        user="tamer"
    )