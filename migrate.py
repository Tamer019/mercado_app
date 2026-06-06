import psycopg2
import psycopg2.extras

RENDER_URL = "postgresql://mercado_db_yoth_user:GJhHVxz2yj8Zz8b4DNi0OSS5zOV8gtv5@dpg-d7of9p8g4nts73alim0g-a.frankfurt-postgres.render.com/mercado_db_yoth?sslmode=require"
NEON_URL   = "postgresql://neondb_owner:npg_5UlvPEa8bcVB@ep-divine-math-aq3jhzlp.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

TABLES = ["angebote", "originalpreise", "merkliste"]

src = psycopg2.connect(RENDER_URL)
dst = psycopg2.connect(NEON_URL)

src_cur = src.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
dst_cur = dst.cursor()

for table in TABLES:
    print(f"Migriere {table}...")
    src_cur.execute(f"SELECT * FROM {table}")
    rows = src_cur.fetchall()
    if not rows:
        print(f"  -> leer, übersprungen")
        continue

    cols = list(rows[0].keys())
    cols_str = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))

    for row in rows:
        values = [row[c] for c in cols]
        dst_cur.execute(
            f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
            values
        )

    dst.commit()
    print(f"  -> {len(rows)} Zeilen migriert")

src.close()
dst.close()
print("Fertig!")
