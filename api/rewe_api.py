import httpx

REWE_SEARCH_URL = "https://shop.rewe.de/api/products"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.rewe.de/",
}

# PLZ → REWE Market ID (Abholservice)
PLZ_MARKT_MAP = {
    "72555": "840881",
}

DEFAULT_MARKT_ID = "840881"


def _markt_id(plz: str) -> str:
    return PLZ_MARKT_MAP.get(plz, DEFAULT_MARKT_ID)


async def suche_rewe_produkte(q: str, plz: str) -> list[dict]:
    markt_id = _markt_id(plz)
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            r = await client.get(REWE_SEARCH_URL, params={
                "search": q,
                "marketId": markt_id,
                "serviceTypes": "PICKUP",
                "pageSize": 20,
            }, headers=HEADERS)
            produkte = r.json().get("_embedded", {}).get("products", [])
    except Exception:
        return []

    ergebnisse = []
    for p in produkte:
        artikel = p.get("_embedded", {}).get("articles", [{}])[0]
        listing = artikel.get("_embedded", {}).get("listing", {})
        pricing = listing.get("pricing", {})

        preis_cents = pricing.get("currentRetailPrice")
        if not preis_cents:
            continue

        preis = round(preis_cents / 100, 2)
        name  = p.get("productName", "")
        bild  = p.get("media", {}).get("images", [{}])[0].get("_links", {}).get("self", {}).get("href")

        ergebnisse.append({
            "produkt":      name,
            "beschreibung": pricing.get("grammage", ""),
            "haendler":     "REWE",
            "preis":        preis,
            "alter_preis":  None,
            "einheit":      pricing.get("grammage", ""),
            "kategorie":    "",
            "gueltig_von":  None,
            "gueltig_bis":  None,
            "ist_angebot":  False,
            "plz_liste":    [plz],
            "quelle":       "rewe",
            "bild_url":     bild,
        })
    return ergebnisse
