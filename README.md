# 🛒 Mercado – Supermarkt Preisvergleich

Ein Web-Scraper + API + Frontend für den Vergleich von Supermarkt-Angeboten (basierend auf Marktguru-Daten).

## 🧠 Projektübersicht

- **Scraper** ruft täglich Angebote von der Marktguru-API ab und speichert sie in einer PostgreSQL-Datenbank.
- **FastAPI-Backend** stellt die gespeicherten Daten über eine Such-API bereit.
- **Frontend** (HTML/CSS/JS) erlaubt die interaktive Suche nach Produkten.
- Initial mit GitHub Copilot CLI begonnen, wird aber manuell weiterentwickelt.

---

## 📦 Tech-Stack

| Bereich       | Technologie                     |
|---------------|--------------------------------|
| Scraping      | Python + `requests`            |
| API           | FastAPI + Uvicorn              |
| Frontend      | Vanilla HTML/CSS/JS            |
| Datenbank     | PostgreSQL                     |
| Server (lokal)| `http.server` (Frontend)       |

---

## 🌳 Ordnerstruktur
mercado/
├── api/
│ └── main.py # FastAPI-Backend
├── scraper/
│ ├── main.py # Haupt-Scraper
│ ├── marktguru.py # API-Aufruf
│ ├── db_connection.py # DB-Verbindung
│ ├── db_save.py # Speichern + Duplikatsprüfung
│ └── db_setup.py # Tabellenerstellung
├── frontend/
│ ├── index.html
│ ├── script.js
│ └── styles.css
├── requirements.txt
├── start.py # Startet Backend + Frontend parallel
└── .gitignore


---

## ⚙️ Setup (lokal)

### 1. Repository klonen

```
git clone <dein-repo-url>
cd mercado
```

### 2. Virtuelle Umgebung erstellen & aktivieren
```
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```


### 3. Abhängigkeiten installieren
```
pip install -r requirements.txt
```

### 4. PostgreSQL einrichten

PostgreSQL installieren.
Datenbank erstellen:
```
CREATE DATABASE mercadodb;
```

Kein Passwort (für lokale Entwicklung).
Die Verbindung nutzt (ggf. anpassen):
```
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,      # oder 5432
    "database": "mercadoDB",
    "user": "tamer"
}
```

### 5. Datenbank-Tabelle erstellen
```
cd scraper
python db_setup.py
```

Tabellenschema:
```
CREATE TABLE IF NOT EXISTS angebote (
    id              SERIAL PRIMARY KEY,
    produkt_name    VARCHAR(200),
    beschreibung    TEXT,
    haendler        VARCHAR(100),
    preis           FLOAT,
    alter_preis     FLOAT,
    einheit         VARCHAR(20),
    kategorie       VARCHAR(100),
    gueltig_von     TIMESTAMP,
    gueltig_bis     TIMESTAMP,
    plz             VARCHAR(10),
    gespeichert_am  TIMESTAMP DEFAULT NOW()
);
```

# 🚀 Starten

Automatisch (Backend + Frontend parallel)

```
python start.py
Backend: http://127.0.0.1:8000
Frontend: http://127.0.0.1:8001 (wird automatisch geöffnet)
```
Manuell

Backend:

```
uvicorn api.main:app --reload --port 8000
```
Frontend (in separatem Terminal):

```
cd frontend
python -m http.server 8001
```

## 🔍 Scraper ausführen

Nur Scraper (ohne API/Frontend):

```
cd scraper
python main.py
```
Scraped folgende Produkte:

```
PRODUKTE = ["walnuss", "mandel", "eier", "milch", "gurke", "tomate"]
PLZ = "72555"
```

## 📡 API-Endpoint
```
GET /search
```
Parameter:
```
Name	Typ	Beispiel	Beschreibung
q	string	mango	Suchbegriff
plz	string	70178	Postleitzahl (optional, default 70178)
```

Beispiel-Request:
```
http://127.0.0.1:8000/search?q=mango&plz=72555
```
Beispiel-Response:
```
json
{
  "suche": "mango",
  "plz": "72555",
  "anzahl": 3,
  "ergebnisse": [
    {
      "produkt": "Mango",
      "preis": 0.99,
      "haendler": "Lidl",
      "gueltig_bis": "2026-05-15T23:59:59"
    }
  ]
}
```
## 🎨 Frontend-Features

Dark Theme mit grünen Akzenten
Eingabe von Suchbegriff + PLZ
Suchergebnisse mit:

Händler-Farben
Angebots-Badge (wenn alter Preis existiert)
Gültigkeitsdatum
Responsive Design

## 🐛 Troubleshooting

Problem	Lösung
```
ModuleNotFoundError	
pip install -r requirements.txt

Datenbankverbindung fehlschlägt	
Prüfe Host/Port/Benutzer in db_connection.py

Port 8000/8001 bereits belegt	
lsof -i :8000 (Mac/Linux) oder anderen Port nutzen

Frontend zeigt "Backend nicht erreichbar"	
Stelle sicher, dass api/main.py läuft

CORS-Fehler	
Ist in api/main.py bereits konfiguriert: allow_origins=["*"]
```
## 🧪 Wichtigste Codezeilen erklärt
API (api/main.py)
```
@app.get("/search")
def suche(q: str, plz: str = "70178"):
    response = requests.get(MARKTGURU_URL, params={...}, headers=HEADERS)
    # Sortiert nach Preis
    ergebnisse.sort(key=lambda x: x["preis"] or 999)
```
Scraper (scraper/marktguru.py)
```
def suche_angebote(suchbegriff, plz="72555"):
    return requests.get(MARKTGURU_URL, params={...}, headers=HEADERS).json().get("results", [])
```
DB Speichern (scraper/db_save.py)

```
# Duplikatsprüfung
cursor.execute("""SELECT id FROM angebote WHERE produkt_name = %s AND haendler = %s AND gueltig_von = %s""")
if cursor.fetchone():
    übersprungen += 1
    continue
```
Frontend (frontend/script.js)

```
const antwort = await fetch(`http://127.0.0.1:8000/search?q=${encodeURIComponent(suchbegriff)}&plz=${plz}`);
const daten = await antwort.json();
```

## 📝 Nächste & mögliche Erweiterungen

CI/CD Pipeline (GitLab CI)

Datenbank-Passwort über .env auslagern

Docker-Container für einfaches Deployment

Mehr Händler / Quellen einbinden

Preisverlauf & Charts

Benachrichtigungen bei Preisänderungen

## 🗑️ Ignorierte Dateien (aus früherer Copilot-Nutzung)

Folgende Dateien existieren im Repo, sind aber nicht relevant für den aktuellen Betrieb:

- .github/github-app/ – für GitHub Copilot CLI
- .gitlab-ci.yml – zukünftige CI/CD
- issues.json – nicht genutzt

## 📄 Lizenz

Privatprojekt – keine spezifische Lizenz.