import httpx

REWE_STORE_URL  = "https://www.rewe.de/api/stores/search"
REWE_SEARCH_URL = "https://www.rewe.de/api/products/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.rewe.de/",
}

_markt_cache: dict[str, str | None] = {}


async def finde_markt_id(plz: str) -> str | None:
    if plz in _markt_cache:
        return _markt_cache[plz]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(REWE_STORE_URL, params={"search": plz, "limit": 1}, headers=HEADERS)
            stores = r.json().get("stores", [])
            markt_id = stores[0].get("id") if stores else None
            _markt_cache[plz] = markt_id
            return markt_id
    except Exception:
        _markt_cache[plz] = None
        return None


async def suche_rewe_produkte(q: str, plz: str) -> list[dict]:
    markt_id = await finde_markt_id(plz)
    if not markt_id:
        return []
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(REWE_SEARCH_URL, params={
                "search": q,
                "marketId": markt_id,
                "serviceTypes": "PICKUP",
                "pageSize": 20,
            }, headers=HEADERS)
            produkte = r.json().get("products", [])
    except Exception:
        return []

    ergebnisse = []
    for p in produkte:
        preis = p.get("pricing", {}).get("currentRetailPrice")
        name  = p.get("name", "")
        if not preis or not name:
            continue
        ergebnisse.append({
            "produkt":      name,
            "beschreibung": p.get("grammage", ""),
            "haendler":     "REWE",
            "preis":        preis,
            "alter_preis":  p.get("pricing", {}).get("regularRetailPrice"),
            "einheit":      p.get("quantityAndUnit", ""),
            "kategorie":    p.get("categoryName", ""),
            "gueltig_von":  None,
            "gueltig_bis":  None,
            "ist_angebot":  p.get("pricing", {}).get("currentRetailPrice") != p.get("pricing", {}).get("regularRetailPrice"),
            "plz_liste":    [plz],
            "quelle":       "rewe",
        })
    return ergebnisse
