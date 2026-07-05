from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import httpx
import secrets
from .db_connection import get_db, init_pool, close_pool
from .rewe_api import suche_rewe_produkte

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

sync_state = {
    "running": False,
    "cancelled": False,
    "last_result": None,
}

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
        async with get_db() as conn:
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
                CREATE TABLE IF NOT EXISTS users (
                    id          SERIAL PRIMARY KEY,
                    username    VARCHAR(100) UNIQUE NOT NULL,
                    erstellt_am TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS merkliste (
                    id              SERIAL PRIMARY KEY,
                    username        VARCHAR(100) NOT NULL,
                    suchbegriff     VARCHAR(200) NOT NULL,
                    plz             VARCHAR(10) NOT NULL DEFAULT '72555',
                    gespeichert_am  TIMESTAMP DEFAULT NOW(),
                    UNIQUE(username, suchbegriff, plz)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS einkaufsliste (
                    id              SERIAL PRIMARY KEY,
                    username        VARCHAR(100) NOT NULL,
                    produkt_name    VARCHAR(200) NOT NULL,
                    haendler        VARCHAR(100) NOT NULL,
                    preis           FLOAT,
                    plz             VARCHAR(10),
                    gespeichert_am  TIMESTAMP DEFAULT NOW(),
                    UNIQUE(username, produkt_name, haendler, plz)
                )
            """)
        print("✅ DB tables ready")
    except Exception as e:
        print(f"❌ DB init error: {e}")

@app.on_event("startup")
async def startup():
    await init_pool()
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    await close_pool()

# ========== USER ENDPOINTS ==========

@app.post("/users/register")
async def register_user(username: str):
    async with get_db() as conn:
        await conn.execute("""
            INSERT INTO users (username)
            VALUES ($1)
            ON CONFLICT (username) DO NOTHING
        """, username)
    return {"message": "Registriert"}

# ========== MERKLISTE ENDPOINTS ==========

@app.get("/merkliste/{username}")
async def get_merkliste(username: str):
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT suchbegriff, plz, gespeichert_am
            FROM merkliste
            WHERE username = $1
            ORDER BY gespeichert_am DESC
        """, username)
    return [dict(r) for r in rows]

@app.post("/merkliste/{username}")
async def add_to_merkliste(username: str, suchbegriff: str, plz: str = "72555"):
    async with get_db() as conn:
        await conn.execute("""
            INSERT INTO merkliste (username, suchbegriff, plz)
            VALUES ($1, $2, $3)
            ON CONFLICT (username, suchbegriff, plz) DO NOTHING
        """, username, suchbegriff, plz)
    return {"message": "Gespeichert"}

@app.delete("/merkliste/{username}")
async def remove_from_merkliste(
    username: str,
    suchbegriff: str = Query(...),
    plz: str = Query(...)
):
    async with get_db() as conn:
        await conn.execute("""
            DELETE FROM merkliste
            WHERE username = $1 AND suchbegriff = $2 AND plz = $3
        """, username, suchbegriff, plz)
    return {"message": "Entfernt"}

# ========== EINKAUFSLISTE ENDPOINTS ==========

@app.get("/einkaufsliste/{username}")
async def get_einkaufsliste(username: str):
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT id, produkt_name, haendler, preis, plz, gespeichert_am
            FROM einkaufsliste
            WHERE username = $1
            ORDER BY gespeichert_am DESC
        """, username)
    return [dict(r) for r in rows]

@app.post("/einkaufsliste/{username}")
async def add_to_einkaufsliste(username: str, produkt_name: str, haendler: str, preis: float, plz: str):
    async with get_db() as conn:
        await conn.execute("""
            INSERT INTO einkaufsliste (username, produkt_name, haendler, preis, plz)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (username, produkt_name, haendler, plz) DO NOTHING
        """, username, produkt_name, haendler, preis, plz)
    return {"message": "Gespeichert"}

@app.delete("/einkaufsliste/{username}/{id}")
async def remove_from_einkaufsliste(username: str, id: int):
    async with get_db() as conn:
        await conn.execute("""
            DELETE FROM einkaufsliste WHERE username = $1 AND id = $2
        """, username, id)
    return {"message": "Entfernt"}

# ========== PUBLIC ENDPOINTS ==========
@app.get("/")
def root():
    return {"message": "Mercado API läuft!"}

@app.get("/suggest")
async def suggest(q: str):
    if len(q) < 2:
        return []
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT produkt_name FROM originalpreise
            WHERE produkt_name ILIKE $1
            UNION
            SELECT DISTINCT produkt_name FROM angebote
            WHERE produkt_name ILIKE $1
            ORDER BY produkt_name
            LIMIT 8
        """, f"%{q}%", f"%{q}%")
    return [row["produkt_name"] for row in rows]

@app.get("/search")
async def suche(q: str, plz: str = "70178"):
    plz_liste = [p.strip() for p in plz.split(",") if p.strip()]

    # 1. Marktguru für jede PLZ abfragen, Ergebnisse nach (haendler, produkt, preis) mergen
    angebote_map = {}
    async with httpx.AsyncClient() as client:
        for p in plz_liste:
            response = await client.get(MARKTGURU_URL, params={
                "as": "web", "limit": 50, "offset": 0, "q": q, "zipCode": p
            }, headers=HEADERS)
            for angebot in response.json().get("results", []):
                haendler = angebot.get("advertisers", [{}])[0].get("name", "")
                if not haendler or not haendler_erlaubt(haendler):
                    continue
                produkt_name = angebot.get("product", {}).get("name", "")
                preis = angebot.get("price")
                key = (haendler, produkt_name, preis)
                if key not in angebote_map:
                    angebote_map[key] = {
                        "produkt": produkt_name,
                        "beschreibung": angebot.get("description", ""),
                        "haendler": haendler,
                        "preis": preis,
                        "alter_preis": angebot.get("oldPrice"),
                        "einheit": angebot.get("unit", {}).get("shortName", ""),
                        "kategorie": angebot.get("categories", [{}])[0].get("name", ""),
                        "gueltig_von": angebot.get("validityDates", [{}])[0].get("from", ""),
                        "gueltig_bis": angebot.get("validityDates", [{}])[0].get("to", ""),
                        "ist_angebot": True,
                        "plz_liste": [p],
                        "bild_url": None,
                        "quelle": "marktguru",
                    }
                elif p not in angebote_map[key]["plz_liste"]:
                    angebote_map[key]["plz_liste"].append(p)

    haendler_mit_angebot = {key[0] for key in angebote_map}

    # 2. Originalpreise aus DB + REWE API parallel abfragen
    import asyncio
    async with get_db() as conn:
        db_rows, rewe_ergebnisse = await asyncio.gather(
            conn.fetch("""
                SELECT produkt_name, haendler, preis, plz
                FROM originalpreise
                WHERE produkt_name ILIKE $1
            """, f"%{q}%"),
            suche_rewe_produkte(q, "72555"),
        )
    rows = db_rows

    # DB-Ergebnisse nach (haendler, produkt, preis) mergen
    db_map = {}
    for row in rows:
        key = (row["haendler"], row["produkt_name"], row["preis"])
        if key not in db_map:
            db_map[key] = {
                "produkt": row["produkt_name"],
                "beschreibung": "Kein aktuelles Angebot",
                "haendler": row["haendler"],
                "preis": row["preis"],
                "alter_preis": None,
                "einheit": "",
                "kategorie": "",
                "gueltig_von": None,
                "gueltig_bis": None,
                "ist_angebot": False,
                "plz_liste": [row["plz"]],
                "bild_url": None,
                "quelle": "db",
            }
        elif row["plz"] not in db_map[key]["plz_liste"]:
            db_map[key]["plz_liste"].append(row["plz"])

    # 3. Zusammenführen
    ergebnisse = list(angebote_map.values())
    for key, entry in db_map.items():
        if key[0] not in haendler_mit_angebot:
            ergebnisse.append(entry)

    # REWE-Ergebnisse hinzufügen (nur wenn kein Marktguru-Treffer für REWE)
    if "REWE" not in haendler_mit_angebot:
        ergebnisse.extend(rewe_ergebnisse)

    ergebnisse.sort(key=lambda x: x["preis"] or 999)

    return JSONResponse(
        content={"suche": q, "plz": plz, "anzahl": len(ergebnisse), "ergebnisse": ergebnisse},
        media_type="application/json; charset=utf-8"
    )

# ========== ADMIN ENDPOINTS ==========

@app.get("/admin/users")
async def get_all_users(auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT u.username,
                   u.erstellt_am,
                   COUNT(DISTINCT m.id) AS merkliste_count,
                   COUNT(DISTINCT e.id) AS einkauf_count
            FROM users u
            LEFT JOIN merkliste m ON m.username = u.username
            LEFT JOIN einkaufsliste e ON e.username = u.username
            GROUP BY u.username, u.erstellt_am
            ORDER BY u.erstellt_am DESC
        """)
    return [dict(r) for r in rows]

@app.get("/admin/users/{username}/merkliste")
async def get_user_merkliste_admin(username: str, auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT id, suchbegriff, plz, gespeichert_am
            FROM merkliste WHERE username = $1
            ORDER BY gespeichert_am DESC
        """, username)
    return [dict(r) for r in rows]

@app.get("/admin/users/{username}/einkaufsliste")
async def get_user_einkaufsliste_admin(username: str, auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT id, produkt_name, haendler, preis, plz, gespeichert_am
            FROM einkaufsliste WHERE username = $1
            ORDER BY gespeichert_am DESC
        """, username)
    return [dict(r) for r in rows]

@app.delete("/admin/users/{username}/merkliste")
async def clear_user_merkliste(username: str, auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        await conn.execute("DELETE FROM merkliste WHERE username = $1", username)
    return {"message": f"Merkliste von {username} geleert"}

@app.delete("/admin/users/{username}/einkaufsliste")
async def clear_user_einkaufsliste(username: str, auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        await conn.execute("DELETE FROM einkaufsliste WHERE username = $1", username)
    return {"message": f"Einkaufsliste von {username} geleert"}

@app.delete("/admin/users/{username}")
async def delete_user_all(username: str, auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        await conn.execute("DELETE FROM merkliste WHERE username = $1", username)
        await conn.execute("DELETE FROM einkaufsliste WHERE username = $1", username)
        await conn.execute("DELETE FROM users WHERE username = $1", username)
    return {"message": f"Alle Daten von {username} gelöscht"}

@app.delete("/admin/merkliste/item/{id}")
async def delete_merkliste_item(id: int, auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        await conn.execute("DELETE FROM merkliste WHERE id = $1", id)
    return {"message": "Gelöscht"}

@app.delete("/admin/einkaufsliste/item/{id}")
async def delete_einkaufsliste_item(id: int, auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        await conn.execute("DELETE FROM einkaufsliste WHERE id = $1", id)
    return {"message": "Gelöscht"}

@app.get("/admin/preise")
async def get_all_originalpreise(auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT id, produkt_name, haendler, plz, preis, quelle, updated_at
            FROM originalpreise
            ORDER BY produkt_name, haendler
        """)
    return [dict(row) for row in rows]

@app.post("/admin/preise")
async def add_originalpreis(
    produkt_name: str,
    haendler: str,
    plz: str,
    preis: float,
    auth: bool = Depends(verify_admin)
):
    async with get_db() as conn:
        await conn.execute("""
            INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
            VALUES ($1, $2, $3, $4, 'admin_manuell')
            ON CONFLICT (produkt_name, haendler, plz)
            DO UPDATE SET preis = EXCLUDED.preis, quelle = 'admin_manuell', updated_at = NOW()
        """, produkt_name, haendler, plz, preis)
    return {"message": "Preis gespeichert"}

@app.delete("/admin/preise/{id}")
async def delete_originalpreis(id: int, auth: bool = Depends(verify_admin)):
    async with get_db() as conn:
        await conn.execute("DELETE FROM originalpreise WHERE id = $1", id)
    return {"message": "Preis gelöscht"}


@app.get("/history")
async def verlauf(q: str, plz: str = "72555"):
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT haendler, preis, alter_preis, gueltig_von
            FROM angebote
            WHERE produkt_name ILIKE $1 AND plz = $2
            ORDER BY haendler, gueltig_von
        """, f"%{q}%", plz)

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


@app.get("/admin/sync-status")
async def get_sync_status(auth: bool = Depends(verify_admin)):
    return {
        "running": sync_state["running"],
        "last_result": sync_state["last_result"],
    }

@app.post("/admin/sync-cancel")
async def cancel_sync(auth: bool = Depends(verify_admin)):
    if not sync_state["running"]:
        return {"message": "Kein Sync läuft"}
    sync_state["cancelled"] = True
    return {"message": "Abbruch angefordert"}

@app.post("/admin/sync-oldprices")
async def sync_oldprices(auth: bool = Depends(verify_admin)):
    from datetime import datetime, timezone

    if sync_state["running"]:
        raise HTTPException(status_code=409, detail="Sync läuft bereits")

    sync_state["running"] = True
    sync_state["cancelled"] = False

    PLZ = "72555"
    gespeichert = 0
    fehler = 0
    abgebrochen = False

    try:
        async with get_db() as conn:
            async with httpx.AsyncClient() as client:
                for kategorie in SYNC_KATEGORIEN:
                    if sync_state["cancelled"]:
                        abgebrochen = True
                        break
                    offset = 0
                    while True:
                        if sync_state["cancelled"]:
                            abgebrochen = True
                            break
                        response = await client.get(MARKTGURU_URL, params={
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
        sync_state["running"] = False
        sync_state["cancelled"] = False
        sync_state["last_result"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gespeichert": gespeichert,
            "fehler": fehler,
            "kategorien": len(SYNC_KATEGORIEN),
            "abgebrochen": abgebrochen,
        }

    return {
        "message": "Sync abgebrochen" if abgebrochen else "Sync abgeschlossen",
        "kategorien": len(SYNC_KATEGORIEN),
        "gespeichert": gespeichert,
        "fehler": fehler,
        "abgebrochen": abgebrochen,
    }