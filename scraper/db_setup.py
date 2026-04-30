from db_connection import get_connection

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS angebote (
            id              SERIAL PRIMARY KEY,
            produkt_name    VARCHAR(200),
            beschreibung    TEXT,
            haendler        VARCHAR(100),
            preis           FLOAT,
            alter_preis     FLOAT,
            einheit         VARCHAR(20),
            kategorie       VARCHAR(100),
            gueltig_von     TIMESTAMP,
            gueltig_bis     TIMESTAMP,
            plz             VARCHAR(10),
            gespeichert_am  TIMESTAMP DEFAULT NOW()
        )
    """)
    
# Neue Tabelle für Originalpreise
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS originalpreise (
            id              SERIAL PRIMARY KEY,
            produkt_name    VARCHAR(200) NOT NULL,
            haendler        VARCHAR(100) NOT NULL,
            plz             VARCHAR(10) NOT NULL,
            preis           FLOAT NOT NULL,
            quelle          VARCHAR(50) DEFAULT 'API',
            updated_at      TIMESTAMP DEFAULT NOW(),
            UNIQUE(produkt_name, haendler, plz)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Tabellen erfolgreich erstellt!")

if __name__ == "__main__":
    create_tables()