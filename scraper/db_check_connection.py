import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        database="mercadoDB",
        user="tamer"
    )
    print("✅ Verbindung erfolgreich!")
    conn.close()

except Exception as e:
    print(f"❌ Fehler: {e}")