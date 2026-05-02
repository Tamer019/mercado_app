from db_connection import get_connection
from datetime import datetime

ERLAUBTE_HAENDLER = ["aldi", "lidl", "rewe", "edeka"]

def haendler_erlaubt(name: str) -> bool:
    name_lower = name.lower()
    return any(h in name_lower for h in ERLAUBTE_HAENDLER)

def save_angebote(angebote, plz):
    conn = get_connection()
    cursor = conn.cursor()

    gespeichert = 0
    übersprungen = 0

    for angebot in angebote:
        produkt_name  = angebot.get("product", {}).get("name", "")
        beschreibung  = angebot.get("description", "")
        haendler      = angebot.get("advertisers", [{}])[0].get("name", "")
        preis         = angebot.get("price")
        alter_preis   = angebot.get("oldPrice")
        einheit       = angebot.get("unit", {}).get("shortName", "")
        kategorie     = angebot.get("categories", [{}])[0].get("name", "")

        if not haendler_erlaubt(haendler):
            continue

        if alter_preis is not None and alter_preis > 0:
            cursor.execute("""
                INSERT INTO originalpreise (produkt_name, haendler, plz, preis, quelle)
                VALUES (%s, %s, %s, %s, 'scraper')
                ON CONFLICT (produkt_name, haendler, plz)
                DO UPDATE SET preis = EXCLUDED.preis, updated_at = NOW()
            """, (produkt_name, haendler, plz, alter_preis))

        dates       = angebot.get("validityDates", [{}])
        gueltig_von = dates[0].get("from", "") if dates else ""
        gueltig_bis = dates[0].get("to", "") if dates else ""

        gueltig_von = datetime.fromisoformat(gueltig_von.replace("Z", "+00:00")) if gueltig_von else None
        gueltig_bis = datetime.fromisoformat(gueltig_bis.replace("Z", "+00:00")) if gueltig_bis else None

        cursor.execute("""
            SELECT id FROM angebote
            WHERE produkt_name = %s AND haendler = %s AND gueltig_von = %s
        """, (produkt_name, haendler, gueltig_von))

        if cursor.fetchone():
            übersprungen += 1
            continue

        cursor.execute("""
            INSERT INTO angebote
                (produkt_name, beschreibung, haendler, preis, alter_preis,
                 einheit, kategorie, gueltig_von, gueltig_bis, plz)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (produkt_name, beschreibung, haendler, preis, alter_preis,
              einheit, kategorie, gueltig_von, gueltig_bis, plz))

        gespeichert += 1

    # 60-Tage-Rotation
    cursor.execute("DELETE FROM angebote WHERE gespeichert_am < NOW() - INTERVAL '60 days'")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ {gespeichert} Angebote gespeichert, {übersprungen} bereits vorhanden.")
