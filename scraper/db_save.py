from db_connection import get_connection
from datetime import datetime

def save_angebote(angebote, plz):
    conn = get_connection()
    cursor = conn.cursor()

    gespeichert = 0
    übersprungen = 0

    for angebot in angebote:
        # Daten aus der API aufbereiten
        produkt_name  = angebot.get("product", {}).get("name", "")
        beschreibung  = angebot.get("description", "")
        haendler      = angebot.get("advertisers", [{}])[0].get("name", "")
        preis         = angebot.get("price")
        alter_preis   = angebot.get("oldPrice")  # Normalpreis!
        einheit       = angebot.get("unit", {}).get("shortName", "")
        kategorie     = angebot.get("categories", [{}])[0].get("name", "")

        # Datum parsen
        dates       = angebot.get("validityDates", [{}])
        gueltig_von = dates[0].get("from", "") if dates else ""
        gueltig_bis = dates[0].get("to", "") if dates else ""

        gueltig_von = datetime.fromisoformat(gueltig_von.replace("Z", "+00:00")) if gueltig_von else None
        gueltig_bis = datetime.fromisoformat(gueltig_bis.replace("Z", "+00:00")) if gueltig_bis else None

        # Duplikat prüfen — gleicher Händler, Produkt und Zeitraum
        cursor.execute("""
            SELECT id FROM angebote
            WHERE produkt_name = %s
            AND haendler = %s
            AND gueltig_von = %s
        """, (produkt_name, haendler, gueltig_von))

        if cursor.fetchone():
            übersprungen += 1
            continue

        # In Datenbank speichern
        cursor.execute("""
            INSERT INTO angebote
                (produkt_name, beschreibung, haendler, preis, alter_preis,
                 einheit, kategorie, gueltig_von, gueltig_bis, plz)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (produkt_name, beschreibung, haendler, preis, alter_preis,
              einheit, kategorie, gueltig_von, gueltig_bis, plz))

        gespeichert += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ {gespeichert} Angebote gespeichert, {übersprungen} bereits vorhanden.")