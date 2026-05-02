from marktguru import hole_alle_angebote
from db_save import save_angebote

PLZ = "72555"

def run():
    print("🚀 Mercado Scraper startet...")
    angebote = hole_alle_angebote(PLZ)
    print(f"📦 {len(angebote)} Angebote von API geladen")
    save_angebote(angebote, PLZ)
    print("✅ Fertig!")

if __name__ == "__main__":
    run()
