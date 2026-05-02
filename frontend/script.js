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

// ── Chart state ──────────────────────────────────────────────────────────────
let aktuellerChart = null;

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
            ticks: { color: '#94a3b8', callback: v => v.toFixed(2) + '€' },
            grid:  { color: 'rgba(255,255,255,0.07)' },
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

// ── Filter state ─────────────────────────────────────────────────────────────
let alleErgebnisse    = [];
let aktiverHaendler   = null;
let aktiveKategorie   = null;
let nurAngebote       = false;
let aktuellerSuchbegriff = '';
let aktuellePlz       = '';

function zeigeFilterBar() {
  const haendlerListe  = [...new Set(alleErgebnisse.map(e => e.haendler).filter(Boolean))].sort();
  const kategorienListe = [...new Set(alleErgebnisse.map(e => e.kategorie).filter(Boolean))].sort();

  let html = '';

  // Händler-Filter
  html += '<div class="filter-gruppe">';
  html += '<span class="filter-label">Händler</span>';
  html += `<button class="filter-btn${aktiverHaendler === null ? ' aktiv' : ''}" onclick="setHaendler(null)">Alle</button>`;
  haendlerListe.forEach(h => {
    html += `<button class="filter-btn${aktiverHaendler === h ? ' aktiv' : ''}" onclick="setHaendler('${h.replace(/'/g, "\\'")}')">${h}</button>`;
  });
  html += '</div>';

  // Kategorie-Filter (nur wenn mehr als eine vorhanden)
  if (kategorienListe.length > 1) {
    html += '<div class="filter-gruppe">';
    html += '<span class="filter-label">Kategorie</span>';
    html += `<button class="filter-btn${aktiveKategorie === null ? ' aktiv' : ''}" onclick="setKategorie(null)">Alle</button>`;
    kategorienListe.forEach(k => {
      html += `<button class="filter-btn${aktiveKategorie === k ? ' aktiv' : ''}" onclick="setKategorie('${k.replace(/'/g, "\\'")}')">${k}</button>`;
    });
    html += '</div>';
  }

  // Nur-Angebote-Toggle
  html += '<div class="filter-gruppe">';
  html += `<button class="filter-btn toggle-btn${nurAngebote ? ' aktiv' : ''}" onclick="toggleNurAngebote()">🔥 Nur Angebote</button>`;
  html += '</div>';

  const bar = document.getElementById('filter-bar');
  bar.innerHTML = html;
  bar.style.display = 'block';
}

function setHaendler(h)   { aktiverHaendler  = h; zeigeFilterBar(); renderErgebnisse(); }
function setKategorie(k)  { aktiveKategorie  = k; zeigeFilterBar(); renderErgebnisse(); }
function toggleNurAngebote() { nurAngebote   = !nurAngebote; zeigeFilterBar(); renderErgebnisse(); }

function renderErgebnisse() {
  let gefiltert = alleErgebnisse;
  if (aktiverHaendler) gefiltert = gefiltert.filter(e => e.haendler === aktiverHaendler);
  if (aktiveKategorie) gefiltert = gefiltert.filter(e => e.kategorie === aktiveKategorie);
  if (nurAngebote)     gefiltert = gefiltert.filter(e => e.ist_angebot === true);

  const total = alleErgebnisse.length;
  const shown = gefiltert.length;
  const filterAktiv = aktiverHaendler || aktiveKategorie || nurAngebote;

  let html = `
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
      <p class="status" style="margin:0;">${filterAktiv ? `${shown} von ${total}` : total} Ergebnisse</p>
      <button class="verlauf-btn" onclick="zeigeVerlauf('${aktuellerSuchbegriff.replace(/'/g, "\\'")}', '${aktuellePlz}')">📈 Preisverlauf</button>
    </div>
  `;

  if (gefiltert.length === 0) {
    html += '<p class="status">Keine Ergebnisse für diesen Filter.</p>';
    document.getElementById('ergebnisse').innerHTML = html;
    return;
  }

  gefiltert.forEach(angebot => {
    const vonDatum = angebot.gueltig_von
      ? new Date(angebot.gueltig_von).toLocaleDateString('de-DE') : '';
    const bisDatum = angebot.gueltig_bis
      ? new Date(angebot.gueltig_bis).toLocaleDateString('de-DE') : '';

    const haendlerKlasse = 'haendler-' + angebot.haendler.toLowerCase().replace(/\s+/g, '');

    let badgeHtml = '';
    let preisHtml = '';

    if (angebot.ist_angebot === true) {
      badgeHtml = '<span class="angebot-badge">🔥 Aktuell im Angebot</span>';
      if (angebot.alter_preis && angebot.alter_preis > 0) {
        preisHtml = `
          <div class="preis">${angebot.preis.toFixed(2)}€
            <span class="statt-preis">statt ${angebot.alter_preis.toFixed(2)}€</span>
          </div>`;
      } else {
        preisHtml = `<div class="preis">${angebot.preis.toFixed(2)}€</div>`;
      }
    } else {
      badgeHtml = '<span class="normalpreis-badge">💰 Normalpreis</span>';
      preisHtml = `<div class="preis normal">${angebot.preis.toFixed(2)}€</div>`;
    }

    html += `
      <div class="ergebnis-karte">
        <div class="haendler ${haendlerKlasse}">${angebot.haendler}</div>
        <div class="produkt-info">
          <div class="produkt-name">${angebot.produkt}</div>
          <div class="beschreibung">${angebot.beschreibung}</div>
          ${angebot.kategorie ? `<div class="gueltigkeit">${angebot.kategorie}</div>` : ''}
          ${vonDatum ? `<div class="gueltigkeit">📅 ${vonDatum} – ${bisDatum}</div>` : ''}
        </div>
        <div class="preis-bereich">
          ${preisHtml}
          ${badgeHtml}
        </div>
      </div>
    `;
  });

  document.getElementById('ergebnisse').innerHTML = html;
}

// ── Search ────────────────────────────────────────────────────────────────────
async function suchen() {
  const suchbegriff    = document.getElementById('suchbegriff').value.trim();
  const plz            = document.getElementById('plz').value.trim();
  const ergebnisseDiv  = document.getElementById('ergebnisse');
  const button         = document.getElementById('such-button');

  if (!suchbegriff) {
    ergebnisseDiv.innerHTML = '<p class="status">Bitte einen Suchbegriff eingeben.</p>';
    return;
  }

  button.disabled     = true;
  button.textContent  = 'Suche...';
  ergebnisseDiv.innerHTML = '<p class="status">⏳ Suche läuft...</p>';
  document.getElementById('filter-bar').style.display = 'none';
  schliesseVerlauf();

  try {
    const antwort = await fetch(`https://mercado-app019.onrender.com/search?q=${encodeURIComponent(suchbegriff)}&plz=${plz}`);
    const daten   = await antwort.json();

    if (daten.anzahl === 0) {
      ergebnisseDiv.innerHTML = '<p class="status">Keine Angebote gefunden. Versuche einen anderen Suchbegriff.</p>';
      return;
    }

    alleErgebnisse       = daten.ergebnisse;
    aktuellerSuchbegriff = suchbegriff;
    aktuellePlz          = plz;
    aktiverHaendler      = null;
    aktiveKategorie      = null;
    nurAngebote          = false;

    zeigeFilterBar();
    renderErgebnisse();

  } catch {
    ergebnisseDiv.innerHTML = '<p class="status">❌ Fehler: Ist der Backend Server gestartet?</p>';
  } finally {
    button.disabled    = false;
    button.textContent = 'Suchen';
  }
}

// ── Enter key ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  ['suchbegriff', 'plz'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') suchen(); });
  });
});
