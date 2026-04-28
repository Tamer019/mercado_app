from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Das erlaubt später unserem Frontend den Backend aufzurufen
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

@app.get("/")
def root():
    return {"message": "Mercado API läuft!"}

@app.get("/search")
def suche(q: str, plz: str = "70178"):
    """
    Produkt suchen und Preise vergleichen.
    Beispiel: /search?q=mango&plz=72555
    """
    response = requests.get(MARKTGURU_URL, params={
        "as": "web",
        "limit": 20,
        "offset": 0,
        "q": q,
        "zipCode": plz
    }, headers=HEADERS)

    daten = response.json()
    angebote = daten.get("results", [])

    # Nur die wichtigsten Felder zurückgeben
    ergebnisse = []
    for angebot in angebote:
        ergebnisse.append({
            "produkt": angebot.get("product", {}).get("name", ""),
            "beschreibung": angebot.get("description", ""),
            "haendler": angebot.get("advertisers", [{}])[0].get("name", ""),
            "preis": angebot.get("price"),
            "alter_preis": angebot.get("oldPrice"),
            "einheit": angebot.get("unit", {}).get("shortName", ""),
            "gueltig_von": angebot.get("validityDates", [{}])[0].get("from", ""),
            "gueltig_bis": angebot.get("validityDates", [{}])[0].get("to", ""),
            "kategorie": angebot.get("categories", [{}])[0].get("name", "")
        })

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