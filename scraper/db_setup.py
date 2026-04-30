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

    # ============================================
    # TESTFALL 1: Admin manuell eingetragener Normalpreis
    # (kein Angebot, nie dagewesen)
    # ============================================
    cursor.execute("""
        INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
        VALUES ('Bio Hafermilch', 'Mein Dorfladen', '72555', 2.49, 'admin_manuell')
        ON CONFLICT (produkt_name, haendler, plz) 
        DO UPDATE SET preis = EXCLUDED.preis, quelle = 'admin_manuell'
    """)

    # ============================================
    # TESTFALL 2: Abgelaufenes Angebot (gescrapt, jetzt nicht mehr aktiv)
    # Originalpreis wurde aus alter_preis gespeichert
    # ============================================
    cursor.execute("""
        INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
        VALUES ('Vegane Butter', 'Supermarkt XY', '72555', 3.99, 'scraper_historisch')
        ON CONFLICT (produkt_name, haendler, plz) 
        DO UPDATE SET preis = EXCLUDED.preis, quelle = 'scraper_historisch'
    """)

    # ============================================
    # TESTFALL 3: Aktuelles Angebot + Originalpreis sichtbar
    # Händler "DemoMarkt" hat aktuell Angebot in API (Mango)
    # ============================================
    cursor.execute("""
        INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
        VALUES ('Mango', 'DemoMarkt', '72555', 2.99, 'api_original')
        ON CONFLICT (produkt_name, haendler, plz) 
        DO UPDATE SET preis = EXCLUDED.preis, quelle = 'api_original'
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Tabellen erfolgreich erstellt!")

if __name__ == "__main__":
    create_tables()