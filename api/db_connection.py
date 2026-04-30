import psycopg2
import os

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "mercadoDB",
    "user": "tamer"
}

def get_connection():
    # Für Render (Production)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    
    # Lokale Entwicklung
    return psycopg2.connect(**DB_CONFIG)
