from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from .db_connection import get_connection


app = FastAPI()

# Das erlaubt später unserem Frontend den Backend aufzurufen
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MARKTGURU_URL = "https://api.marktguru.de/api/v1/offers/search"
HEADERS = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
}

# Datenbank-Initialisierung (Tabelle erstellen, falls nicht vorhanden)
async def init_db():
    try:
        conn = await get_connection()
        await conn.execute("""
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
        # ============================================
        await conn.execute("""
            INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
            VALUES ('Bio Hafermilch', 'Mein Dorfladen', '72555', 2.49, 'admin_manuell')
            ON CONFLICT (produkt_name, haendler, plz) 
            DO UPDATE SET preis = EXCLUDED.preis, quelle = 'admin_manuell'
        """)
        
        # ============================================
        # TESTFALL 2: Abgelaufenes Angebot (gescrapt)
        # ============================================
        await conn.execute("""
            INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
            VALUES ('Vegane Butter', 'Supermarkt XY', '72555', 3.99, 'scraper_historisch')
            ON CONFLICT (produkt_name, haendler, plz) 
            DO UPDATE SET preis = EXCLUDED.preis, quelle = 'scraper_historisch'
        """)
        
        # ============================================
        # TESTFALL 3: Aktuelles Angebot + Originalpreis
        # ============================================
        await conn.execute("""
            INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
            VALUES ('Mango', 'DemoMarkt', '72555', 2.99, 'api_original')
            ON CONFLICT (produkt_name, haendler, plz) 
            DO UPDATE SET preis = EXCLUDED.preis, quelle = 'api_original'
        """)
        
        await conn.close()
        print("✅ Tabelle 'originalpreise' ist bereit")
    except Exception as e:
        print(f"❌ Fehler bei DB-Initialisierung: {e}")

# Startup-Event: Läuft einmal beim Start
@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/")
def root():
    return {"message": "Mercado API läuft!"}

@app.get("/search")
async def suche(q: str, plz: str = "70178"):
#def suche(q: str, plz: str = "70178"):
    """
    Produkt suchen und Preise vergleichen.
    Beispiel: /search?q=mango&plz=72555
    """
# 1. Aktuelle Angebote von Marktguru API holen
    response = requests.get(MARKTGURU_URL, params={
        "as": "web",
        "limit": 50,
        "offset": 0,
        "q": q,
        "zipCode": plz
    }, headers=HEADERS)

    daten = response.json()
    api_angebote = daten.get("results", [])
    
# 2. Alle Händler aus den API-Angeboten sammeln
    haendler_mit_angebot = {}
    for angebot in api_angebote:
        haendler = angebot.get("advertisers", [{}])[0].get("name", "")
        if haendler:
            haendler_mit_angebot[haendler] = {
                "produkt": angebot.get("product", {}).get("name", ""),
                "beschreibung": angebot.get("description", ""),
                "preis": angebot.get("price"),
                "alter_preis": angebot.get("oldPrice"),
                "einheit": angebot.get("unit", {}).get("shortName", ""),
                "kategorie": angebot.get("categories", [{}])[0].get("name", ""),
                "gueltig_von": angebot.get("validityDates", [{}])[0].get("from", ""),
                "gueltig_bis": angebot.get("validityDates", [{}])[0].get("to", ""),
                "ist_angebot": True
            }

 # 3. Originalpreise aus DB holen
    conn = await get_connection()
    
    rows = await conn.fetch("""
        SELECT produkt_name, haendler, preis 
        FROM originalpreise 
        WHERE produkt_name ILIKE $1 AND plz = $2
    """, f"%{q}%", plz)
    
    await conn.close()

    # 4. Ergebnisse mergen
    # Nur die wichtigsten Felder zurückgeben
    ergebnisse = []

# Zuerst alle API-Angebote hinzufügen
    for haendler, daten in haendler_mit_angebot.items():
        ergebnisse.append({
            "produkt": daten["produkt"],
            "beschreibung": daten["beschreibung"],
            "haendler": haendler,
            "preis": daten["preis"],
            "alter_preis": daten["alter_preis"],
            "einheit": daten["einheit"],
            "kategorie": daten["kategorie"],
            "gueltig_von": daten["gueltig_von"],
            "gueltig_bis": daten["gueltig_bis"],
            "ist_angebot": True
        })

    # Dann Händler aus DB hinzufügen, die KEIN Angebot haben
    for row in rows:
        produkt_name_db, haendler_db, preis_db = row
        if haendler_db not in haendler_mit_angebot:
            ergebnisse.append({
                "produkt": produkt_name_db,
                "beschreibung": "Kein aktuelles Angebot",
                "haendler": haendler_db,
                "preis": preis_db,
                "alter_preis": None,
                "einheit": "",
                "kategorie": "",
                "gueltig_von": None,
                "gueltig_bis": None,
                "ist_angebot": False
            })
# auskommentiert, da wir jetzt alle Händler (mit und ohne Angebot) in der ersten Schleife hinzufügen
#    for angebot in angebote:
#        ergebnisse.append({
#            "produkt": angebot.get("product", {}).get("name", ""),
#            "beschreibung": angebot.get("description", ""),
#            "haendler": angebot.get("advertisers", [{}])[0].get("name", ""),
#            "preis": angebot.get("price"),
#            "alter_preis": angebot.get("oldPrice"),
#            "einheit": angebot.get("unit", {}).get("shortName", ""),
#            "gueltig_von": angebot.get("validityDates", [{}])[0].get("from", ""),
#            "gueltig_bis": angebot.get("validityDates", [{}])[0].get("to", ""),
#            "kategorie": angebot.get("categories", [{}])[0].get("name", "")
#        })

    # Nach Preis sortieren
    ergebnisse.sort(key=lambda x: x["preis"] or 999)

    return JSONResponse(
        content={
            "suche": q,
            "plz": plz,
            "anzahl": len(ergebnisse),
            "ergebnisse": ergebnisse
        },
        media_type="application/json; charset=utf-8"
)



