const HAENDLER_FARBEN = {
  'lidl':      '#60a5fa',
  'aldi':      '#4ade80',
  'rewe':      '#fb7185',
  'edeka':     '#fbbf24',
  'kaufland':  '#c084fc',
  'penny':     '#f97316',
  'netto':     '#34d399',
};

const FARB_PALETTE = ['#4ade80','#60a5fa','#fb7185','#fbbf24','#c084fc','#f97316','#34d399','#e879f9'];

function haendlerFarbe(name, index) {
  const key = name.toLowerCase().replace(/\s+/g, '');
  return HAENDLER_FARBEN[key] || FARB_PALETTE[index % FARB_PALETTE.length];
}

let aktuellerChart = null;
let aktuellerSuchbegriff = '';

async function zeigeVerlauf(q, plz) {
  const section = document.getElementById('verlauf-section');
  const status  = document.getElementById('verlauf-status');
  const titel   = document.getElementById('verlauf-titel');

  section.style.display = 'block';
  status.textContent    = '⏳ Lade Preisverlauf...';
  titel.textContent     = `📈 Preisverlauf: ${q}`;
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });

  if (aktuellerChart) { aktuellerChart.destroy(); aktuellerChart = null; }

  try {
    const antwort = await fetch(`https://mercado-app019.onrender.com/history?q=${encodeURIComponent(q)}&plz=${plz}`);
    const daten   = await antwort.json();

    if (daten.anzahl_eintraege === 0) {
      status.textContent = 'Keine historischen Daten vorhanden. Der Scraper muss zuerst Daten sammeln.';
      return;
    }

    // Collect and sort all unique dates across all retailers
    const alleDaten = [...new Set(
      daten.verlauf.flatMap(v => v.eintraege.map(e => e.datum).filter(Boolean))
    )].sort();

    const labels = alleDaten.map(d => new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }));

    const datasets = daten.verlauf.map((v, i) => {
      const farbe = haendlerFarbe(v.haendler, i);
      const datumZuPreis = Object.fromEntries(v.eintraege.filter(e => e.datum).map(e => [e.datum, e.preis]));
      return {
        label: v.haendler,
        data: alleDaten.map(d => datumZuPreis[d] ?? null),
        borderColor: farbe,
        backgroundColor: farbe + '22',
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.3,
        spanGaps: false,
      };
    });

    const ctx = document.getElementById('verlaufChart').getContext('2d');
    aktuellerChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#e0e0e0', padding: 16 } },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(2)}€`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#94a3b8' },
            grid:  { color: 'rgba(255,255,255,0.07)' },
          },
          y: {
            ticks: {
              color: '#94a3b8',
              callback: v => v.toFixed(2) + '€',
            },
            grid: { color: 'rgba(255,255,255,0.07)' },
          },
        },
      },
    });

    status.textContent = `${daten.anzahl_eintraege} Einträge aus der Datenbank`;
  } catch {
    status.textContent = '❌ Fehler beim Laden des Preisverlaufs.';
  }
}

function schliesseVerlauf() {
  document.getElementById('verlauf-section').style.display = 'none';
  if (aktuellerChart) { aktuellerChart.destroy(); aktuellerChart = null; }
}

// Search functionality

async function suchen() {
  const suchbegriff = document.getElementById('suchbegriff').value.trim();
  const plz = document.getElementById('plz').value.trim();
  const ergebnisseDiv = document.getElementById('ergebnisse');
  const button = document.getElementById('such-button');

  // Do nothing if search field is empty
  if (!suchbegriff) {
    ergebnisseDiv.innerHTML = '<p class="status">Bitte einen Suchbegriff eingeben.</p>';
    return;
  }

  // Show loading animation
  button.disabled = true;
  button.textContent = 'Suche...';
  ergebnisseDiv.innerHTML = '<p class="status">⏳ Suche läuft...</p>';
  schliesseVerlauf();

  try {
    // Call backend
    // const antwort = await fetch(`http://127.0.0.1:8000/search?q=${encodeURIComponent(suchbegriff)}&plz=${plz}`);
    const antwort = await fetch(`https://mercado-app019.onrender.com/search?q=${encodeURIComponent(suchbegriff)}&plz=${plz}`);
    const daten = await antwort.json();

    if (daten.anzahl === 0) {
      ergebnisseDiv.innerHTML = '<p class="status">Keine Angebote gefunden. Versuche einen anderen Suchbegriff.</p>';
      return;
    }

    aktuellerSuchbegriff = suchbegriff;

    // Display results
    let html = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <p class="status" style="margin:0;">${daten.anzahl} Angebote gefunden</p>
        <button class="verlauf-btn" onclick="zeigeVerlauf('${suchbegriff.replace(/'/g, "\\'")}', '${plz}')">📈 Preisverlauf anzeigen</button>
      </div>
    `;

    daten.ergebnisse.forEach(angebot => {
      // Format dates nicely
      const vonDatum = angebot.gueltig_von
        ? new Date(angebot.gueltig_von).toLocaleDateString('de-DE')
        : '';
      const bisDatum = angebot.gueltig_bis
        ? new Date(angebot.gueltig_bis).toLocaleDateString('de-DE')
        : '';

      // Prepare retailer class name for coloring
      const haendlerKlasse = 'haendler-' + angebot.haendler.toLowerCase().replace(/\s+/g, '');

      // Show offer badge if there's an old price
      //const angebotBadge = angebot.alter_preis
      //  ? `<span class="angebot-badge">Angebot</span>`
      //  : '';

// 🔥 NEU: Anzeige basierend auf ist_angebot
      let badgeHtml = '';
      let preisHtml = '';

      if (angebot.ist_angebot === true) {
        badgeHtml = '<span class="angebot-badge">🔥 Aktuell im Angebot</span>';
        if (angebot.alter_preis && angebot.alter_preis > 0) {
          preisHtml = `
            <div class="preis">${angebot.preis.toFixed(2)}€ 
              <span class="statt-preis">statt ${angebot.alter_preis.toFixed(2)}€</span>
            </div>
          `;
        } else {
          preisHtml = `<div class="preis">${angebot.preis.toFixed(2)}€</div>`;
        }
      } else {
        badgeHtml = '<span class="normalpreis-badge">💰 Normalpreis (kein Angebot)</span>';
        preisHtml = `<div class="preis normal">${angebot.preis.toFixed(2)}€</div>`;
      }
      
      //const alterPreis = angebot.alter_preis
      //  ? `<div class="alter-preis">statt ${angebot.alter_preis.toFixed(2)}€</div>`
      //  : '';

      html += `
        <div class="ergebnis-karte">
          <div class="haendler ${haendlerKlasse}">${angebot.haendler}</div>
          <div class="produkt-info">
            <div class="produkt-name">${angebot.produkt}</div>
            <div class="beschreibung">${angebot.beschreibung}</div>
            ${vonDatum ? `<div class="gueltigkeit">📅 ${vonDatum} – ${bisDatum}</div>` : ''}
          </div>
          <div class="preis-bereich">
            ${preisHtml}
            ${badgeHtml}
          </div>
        </div>
      `;
    });

    ergebnisseDiv.innerHTML = html;

  } catch (fehler) {
    ergebnisseDiv.innerHTML = '<p class="status">❌ Fehler: Ist der Backend Server gestartet?</p>';
  } finally {
    button.disabled = false;
    button.textContent = 'Suchen';
  }
}

// Allow Enter key to submit search
document.addEventListener('DOMContentLoaded', function() {
  const suchbegriffInput = document.getElementById('suchbegriff');
  const plzInput = document.getElementById('plz');

  if (suchbegriffInput) {
    suchbegriffInput.addEventListener('keydown', function(event) {
      if (event.key === 'Enter') {
        suchen();
      }
    });
  }

  if (plzInput) {
    plzInput.addEventListener('keydown', function(event) {
      if (event.key === 'Enter') {
        suchen();
      }
    });
  }
});
