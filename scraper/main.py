from marktguru import suche_angebote
from db_save import save_angebote

# Liste der Produkte die täglich gescrapt werden
PRODUKTE = [
    "walnuss",
    "mandel",
    "eier",
    "milch",
    "gurke",
    "tomate",
]

PLZ = "72555"

def run():
    print("🚀 Mercado Scraper startet...\n")
    for produkt in PRODUKTE:
        print(f"🔍 Suche: {produkt}")
        angebote = suche_angebote(produkt, PLZ)
        print(f"📦 {len(angebote)} Angebote gefunden")
        save_angebote(angebote, PLZ)
    print("\n✅ Fertig!")

if __name__ == "__main__":
    run()