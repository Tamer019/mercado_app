from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import requests
import secrets
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

ERLAUBTE_HAENDLER = ["aldi", "lidl", "rewe", "edeka"]

SYNC_KATEGORIEN = [
    "obst", "gemüse", "fleisch", "wurst", "fisch",
    "milch", "käse", "joghurt", "eier", "butter",
    "brot", "getränke", "saft", "snacks", "tiefkühl",
    "öl", "reis", "nudeln", "konserven", "süßigkeiten",
]

def haendler_erlaubt(name: str) -> bool:
    name_lower = name.lower()
    return any(h in name_lower for h in ERLAUBTE_HAENDLER)

# Admin Auth (Hardcoded für den Anfang)
security = HTTPBasic()
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "mercado19"

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# Datenbank-Initialisierung (Tabelle erstellen, falls nicht vorhanden)
async def init_db():
    try:
        conn = await get_connection()
        await conn.execute("""
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
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS originalpreise (
                id              SERIAL PRIMARY KEY,
                produkt_name    VARCHAR(200) NOT NULL,
                haendler        VARCHAR(100) NOT NULL,
                plz             VARCHAR(10) NOT NULL,
                preis           FLOAT NOT NULL,
                quelle          VARCHAR(50) DEFAULT 'scraper',
                updated_at      TIMESTAMP DEFAULT NOW(),
                UNIQUE(produkt_name, haendler, plz)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS wunschliste (
                id              SERIAL PRIMARY KEY,
                username        VARCHAR(100) NOT NULL,
                produkt_name    VARCHAR(200) NOT NULL,
                haendler        VARCHAR(100) NOT NULL,
                preis           FLOAT,
                alter_preis     FLOAT,
                ist_angebot     BOOLEAN DEFAULT FALSE,
                plz             VARCHAR(10),
                einheit         VARCHAR(20),
                gueltig_bis     TIMESTAMP,
                gespeichert_am  TIMESTAMP DEFAULT NOW(),
                UNIQUE(username, produkt_name, haendler)
            )
        """)
        await conn.close()
        print("✅ DB tables ready")
    except Exception as e:
        print(f"❌ DB init error: {e}")

# Startup-Event: Läuft einmal beim Start
@app.on_event("startup")
async def startup():
    await init_db()

# ========== WISHLIST ENDPOINTS ==========

class WunschlistenItem(BaseModel):
    produkt_name: str
    haendler: str
    preis: Optional[float] = None
    alter_preis: Optional[float] = None
    ist_angebot: bool = False
    plz: str = "72555"
    einheit: str = ""
    gueltig_bis: Optional[str] = None

@app.get("/wishlist/{username}")
async def get_wishlist(username: str):
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT id, produkt_name, haendler, preis, alter_preis, ist_angebot,
               plz, einheit, gueltig_bis, gespeichert_am
        FROM wunschliste
        WHERE username = $1
        ORDER BY gespeichert_am DESC
    """, username)
    await conn.close()
    return [dict(r) for r in rows]

@app.post("/wishlist/{username}")
async def add_to_wishlist(username: str, item: WunschlistenItem):
    gueltig_bis = None
    if item.gueltig_bis:
        from datetime import datetime
        try:
            gueltig_bis = datetime.fromisoformat(item.gueltig_bis.replace("Z", "+00:00"))
        except ValueError:
            pass

    conn = await get_connection()
    await conn.execute("""
        INSERT INTO wunschliste
            (username, produkt_name, haendler, preis, alter_preis,
             ist_angebot, plz, einheit, gueltig_bis)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        ON CONFLICT (username, produkt_name, haendler) DO NOTHING
    """, username, item.produkt_name, item.haendler, item.preis,
         item.alter_preis, item.ist_angebot, item.plz, item.einheit, gueltig_bis)
    await conn.close()
    return {"message": "Gespeichert"}

@app.delete("/wishlist/{username}")
async def remove_from_wishlist(
    username: str,
    produkt_name: str = Query(...),
    haendler: str = Query(...)
):
    conn = await get_connection()
    await conn.execute("""
        DELETE FROM wunschliste
        WHERE username = $1 AND produkt_name = $2 AND haendler = $3
    """, username, produkt_name, haendler)
    await conn.close()
    return {"message": "Entfernt"}

# ========== PUBLIC ENDPOINTS ==========
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
        if haendler and haendler_erlaubt(haendler):
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

# ========== ADMIN ENDPOINTS ==========

@app.get("/admin/preise")
async def get_all_originalpreise(auth: bool = Depends(verify_admin)):
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT id, produkt_name, haendler, plz, preis, quelle, updated_at
        FROM originalpreise
        ORDER BY produkt_name, haendler
    """)
    await conn.close()
    return [dict(row) for row in rows]

@app.post("/admin/preise")
async def add_originalpreis(
    produkt_name: str, 
    haendler: str, 
    plz: str, 
    preis: float,
    auth: bool = Depends(verify_admin)
):
    conn = await get_connection()
    await conn.execute("""
        INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
        VALUES ($1, $2, $3, $4, 'admin_manuell')
        ON CONFLICT (produkt_name, haendler, plz)
        DO UPDATE SET preis = EXCLUDED.preis, quelle = 'admin_manuell', updated_at = NOW()
    """, produkt_name, haendler, plz, preis)
    await conn.close()
    return {"message": "Preis gespeichert"}

@app.delete("/admin/preise/{id}")
async def delete_originalpreis(id: int, auth: bool = Depends(verify_admin)):
    conn = await get_connection()
    await conn.execute("DELETE FROM originalpreise WHERE id = $1", id)
    await conn.close()
    return {"message": "Preis gelöscht"}


@app.get("/history")
async def verlauf(q: str, plz: str = "72555"):
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT haendler, preis, alter_preis, gueltig_von
        FROM angebote
        WHERE produkt_name ILIKE $1 AND plz = $2
        ORDER BY haendler, gueltig_von
    """, f"%{q}%", plz)
    await conn.close()

    haendler_map = {}
    for row in rows:
        h = row["haendler"]
        if h not in haendler_map:
            haendler_map[h] = []
        haendler_map[h].append({
            "datum": row["gueltig_von"].isoformat() if row["gueltig_von"] else None,
            "preis": row["preis"],
            "alter_preis": row["alter_preis"],
        })

    return JSONResponse(
        content={
            "suche": q,
            "plz": plz,
            "anzahl_eintraege": len(rows),
            "verlauf": [
                {"haendler": h, "eintraege": e}
                for h, e in haendler_map.items()
            ],
        },
        media_type="application/json; charset=utf-8",
    )


@app.post("/admin/sync-oldprices")
async def sync_oldprices(auth: bool = Depends(verify_admin)):
    PLZ = "72555"
    gespeichert = 0
    fehler = 0

    conn = await get_connection()
    try:
        for kategorie in SYNC_KATEGORIEN:
            offset = 0
            while True:
                response = requests.get(MARKTGURU_URL, params={
                    "as": "web",
                    "limit": 50,
                    "offset": offset,
                    "q": kategorie,
                    "zipCode": PLZ
                }, headers=HEADERS)

                angebote = response.json().get("results") or []

                for angebot in angebote:
                    haendler     = angebot.get("advertisers", [{}])[0].get("name", "")
                    alter_preis  = angebot.get("oldPrice")
                    produkt_name = angebot.get("product", {}).get("name", "")

                    if not (haendler_erlaubt(haendler) and alter_preis and alter_preis > 0 and produkt_name):
                        continue
                    try:
                        await conn.execute("""
                            INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
                            VALUES ($1, $2, $3, $4, 'api_sync')
                            ON CONFLICT (produkt_name, haendler, plz)
                            DO UPDATE SET preis = EXCLUDED.preis, quelle = 'api_sync', updated_at = NOW()
                        """, produkt_name, haendler, PLZ, alter_preis)
                        gespeichert += 1
                    except Exception as e:
                        fehler += 1
                        print(f"DB Fehler: {e}")

                if len(angebote) < 50:
                    break
                offset += 50
    finally:
        await conn.close()

    return {
        "message": "Sync abgeschlossen",
        "kategorien": len(SYNC_KATEGORIEN),
        "gespeichert": gespeichert,
        "fehler": fehler,
    }