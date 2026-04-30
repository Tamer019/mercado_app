from db_connection import get_connection

def show_originalpreise():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT produkt_name, haendler, plz, preis, quelle, updated_at FROM originalpreise LIMIT 10")
    for row in cursor.fetchall():
        print(row)
    cursor.close()
    conn.close()

if __name__ == "__main__":
    show_originalpreise()