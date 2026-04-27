import requests

# Deine Postleitzahl hier eintragen
PLZ = "72555"  # Beispiel Stuttgart, kannst du ändern

# Das ist die Marktguru API Adresse
url = "https://api.marktguru.de/api/v1/offers/search"

# Parameter für die Suche
params = {
    "as": "web",
    "limit": 10,
    "offset": 0,
    "q": "walnuss",  # Was wir suchen
    "zipCode": PLZ
}

# Diese Keys brauchen wir um die API zu nutzen
headers = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
}

# API aufrufen
print("Suche nach Walnuss Angeboten...")
response = requests.get(url, params=params, headers=headers)

# Ergebnis anzeigen
if response.status_code == 200:
    daten = response.json()
    angebote = daten.get("results", [])
    print(f"{len(angebote)} Angebote gefunden:\n")
    for angebot in angebote:
        name = angebot.get("description", "Unbekannt")
        preis = angebot.get("price", "?")
        haendler = angebot.get("advertisers", [{}])[0].get("name", "Unbekannt")
        print(f"  {haendler}: {name} — {preis}€")
else:
    print(f"Fehler: {response.status_code}")