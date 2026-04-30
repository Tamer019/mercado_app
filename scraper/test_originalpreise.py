from db_connection import get_connection

def show_originalpreise():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT produkt_name, haendler, plz, preis, quelle, updated_at 
        FROM originalpreise 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    
    if not rows:
        print("❌ Keine Originalpreise gefunden.")
    else:
        print(f"✅ {len(rows)} Originalpreise gefunden:\n")
        for row in rows:
            print(f"Produkt: {row[0]}, Händler: {row[1]}, PLZ: {row[2]}, Preis: {row[3]}€, Quelle: {row[4]}, Updated: {row[5]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    show_originalpreise()