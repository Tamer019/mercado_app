import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "mercadoDB",
    "user": "tamer"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)