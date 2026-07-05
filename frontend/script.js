// ── Info popover ──────────────────────────────────────────────────────────────
let activeInfoBtn = null;

function toggleInfo(event, text) {
  event.stopPropagation();
  const btn = event.currentTarget;
  const popover = document.getElementById('info-popover');

  if (activeInfoBtn === btn) {
    popover.style.display = 'none';
    activeInfoBtn = null;
    return;
  }

  popover.textContent = text;
  popover.style.display = 'block';

  const rect = btn.getBoundingClientRect();
  let top  = rect.bottom + 8;
  let left = rect.left;

  if (left + 250 > window.innerWidth) left = window.innerWidth - 258;
  if (top + 100 > window.innerHeight) top = rect.top - popover.offsetHeight - 8;

  popover.style.top  = top + 'px';
  popover.style.left = left + 'px';
  activeInfoBtn = btn;
}

document.addEventListener('click', () => {
  const popover = document.getElementById('info-popover');
  if (popover) popover.style.display = 'none';
  activeInfoBtn = null;
});

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
  status.textContent    = 'Lade Preisverlauf...';
  titel.textContent     = `Preisverlauf: ${q}`;
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });

  if (aktuellerChart) { aktuellerChart.destroy(); aktuellerChart = null; }

  try {
    const antwort = await fetch(`${API}/history?q=${encodeURIComponent(q)}&plz=${plz}`);
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
    status.textContent = 'Fehler beim Laden des Preisverlaufs.';
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
let aktiveSortierung  = 'preis-asc';
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
  html += `<button class="filter-btn toggle-btn${nurAngebote ? ' aktiv' : ''}" onclick="toggleNurAngebote()">Nur Angebote</button>`;
  html += `<button class="info-btn" onclick="toggleInfo(event, 'Zeigt nur Produkte, die aktuell im Angebot sind. Einträge mit Normalpreis aus der Datenbank werden ausgeblendet.')">?</button>`;
  html += '</div>';

  // Sortierung
  const sortOptionen = [
    { key: 'preis-asc',  label: 'Preis ↑' },
    { key: 'preis-desc', label: 'Preis ↓' },
    { key: 'name-asc',   label: 'Name A→Z' },
    { key: 'name-desc',  label: 'Name Z→A' },
  ];
  html += '<div class="filter-gruppe">';
  html += '<span class="filter-label">Sortierung</span>';
  sortOptionen.forEach(s => {
    html += `<button class="filter-btn${aktiveSortierung === s.key ? ' aktiv' : ''}" onclick="setSortierung('${s.key}')">${s.label}</button>`;
  });
  html += '</div>';

  const bar = document.getElementById('filter-bar');
  bar.innerHTML = html;
  bar.style.display = 'block';
}

function setHaendler(h)      { aktiverHaendler  = h; zeigeFilterBar(); renderErgebnisse(); }
function setKategorie(k)     { aktiveKategorie  = k; zeigeFilterBar(); renderErgebnisse(); }
function toggleNurAngebote() { nurAngebote = !nurAngebote; zeigeFilterBar(); renderErgebnisse(); }
function setSortierung(s)    { aktiveSortierung = s; zeigeFilterBar(); renderErgebnisse(); }

function sortiereErgebnisse(arr) {
  return [...arr].sort((a, b) => {
    switch (aktiveSortierung) {
      case 'preis-asc':  return (a.preis ?? 999) - (b.preis ?? 999);
      case 'preis-desc': return (b.preis ?? 0)   - (a.preis ?? 0);
      case 'name-asc':   return (a.produkt || '').localeCompare(b.produkt || '', 'de');
      case 'name-desc':  return (b.produkt || '').localeCompare(a.produkt || '', 'de');
      default:           return 0;
    }
  });
}

function istExakterTreffer(produktName, suchbegriff) {
  if (!produktName || !suchbegriff) return false;
  const term = suchbegriff.toLowerCase().trim();
  const tokens = produktName.toLowerCase().split(/[\s\-\/,.()\[\]]+/);
  return tokens.some(t => t === term);
}

function renderErgebnisse() {
  let gefiltert = alleErgebnisse;
  if (aktiverHaendler) gefiltert = gefiltert.filter(e => e.haendler === aktiverHaendler);
  if (aktiveKategorie) gefiltert = gefiltert.filter(e => e.kategorie === aktiveKategorie);
  if (nurAngebote)     gefiltert = gefiltert.filter(e => e.ist_angebot === true);

  const total = alleErgebnisse.length;
  const shown = gefiltert.length;
  const filterAktiv = aktiverHaendler || aktiveKategorie || nurAngebote;

  const gemerkt = merklisteItems.has(`${aktuellerSuchbegriff}|${aktuellePlz}`);
  let html = `
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
      <p class="status" style="margin:0;">${filterAktiv ? `${shown} von ${total}` : total} Ergebnisse</p>
      <div style="display:flex; gap:8px; flex-wrap:wrap;">
        <div style="display:flex; align-items:center; gap:6px;">
          <button id="merken-btn" class="merken-btn ${gemerkt ? 'gemerkt' : ''}" onclick="toggleMerken()">
            ${gemerkt ? 'Gemerkt' : 'Merken'}
          </button>
          <button class="info-btn" onclick="toggleInfo(event, 'Speichert diese Suche in deiner Wunschliste. Du kannst sie später über den Wunschliste-Button oben jederzeit aufrufen.')">?</button>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          <button class="verlauf-btn" onclick="zeigeVerlauf('${aktuellerSuchbegriff.replace(/'/g, "\\'")}', '${aktuellePlz}')">Preisverlauf</button>
          <button class="info-btn" onclick="toggleInfo(event, 'Zeigt historische Preisdaten aus der Datenbank.')">?</button>
        </div>
      </div>
    </div>
  `;

  if (gefiltert.length === 0) {
    html += '<p class="status">Keine Ergebnisse für diesen Filter.</p>';
    document.getElementById('ergebnisse').innerHTML = html;
    return;
  }

  gefiltert = sortiereErgebnisse(gefiltert);
  const exakt    = gefiltert.filter(e => istExakterTreffer(e.produkt, aktuellerSuchbegriff));
  const weiteres = gefiltert.filter(e => !istExakterTreffer(e.produkt, aktuellerSuchbegriff));

  const QUELL_BADGE = {
    'marktguru':    { label: 'MG',  title: 'Marktguru API',    color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
    'rewe':         { label: 'RW',  title: 'REWE Online',      color: '#fb7185', bg: 'rgba(251,113,133,0.12)' },
    'api_sync':     { label: 'API', title: 'API-Sync',         color: '#4ade80', bg: 'rgba(74,222,128,0.12)' },
    'admin_manuell':{ label: 'ADM', title: 'Manuell erfasst',  color: '#c084fc', bg: 'rgba(192,132,252,0.12)' },
    'scraper':      { label: 'SC',  title: 'Scraper',          color: '#f97316', bg: 'rgba(249,115,22,0.12)' },
    'db':           { label: 'DB',  title: 'Datenbank',        color: '#94a3b8', bg: 'rgba(148,163,184,0.1)'  },
  };

  function quellBadgeHtml(quelle) {
    const q = QUELL_BADGE[quelle] || { label: quelle?.slice(0,3).toUpperCase() || '?', title: quelle || 'Unbekannt', color: '#64748b', bg: 'rgba(100,116,139,0.1)' };
    return `<span title="${q.title}" style="
      font-size:10px; font-weight:700; letter-spacing:0.04em;
      color:${q.color}; background:${q.bg};
      border:1px solid ${q.color}33;
      border-radius:4px; padding:1px 5px;
      position:absolute; top:8px; right:8px;
      cursor:default; user-select:none;
    ">${q.label}</span>`;
  }

  function karteHtml(angebot) {
    const vonDatum = angebot.gueltig_von
      ? new Date(angebot.gueltig_von).toLocaleDateString('de-DE') : '';
    const bisDatum = angebot.gueltig_bis
      ? new Date(angebot.gueltig_bis).toLocaleDateString('de-DE') : '';
    const haendlerKlasse = 'haendler-' + angebot.haendler.toLowerCase().replace(/\s+/g, '');
    let badgeHtml = '';
    let preisHtml = '';
    if (angebot.ist_angebot === true) {
      badgeHtml = '<span class="angebot-badge">Aktuell im Angebot</span>';
      preisHtml = angebot.alter_preis && angebot.alter_preis > 0
        ? `<div class="preis">${angebot.preis.toFixed(2)}€ <span class="statt-preis">statt ${angebot.alter_preis.toFixed(2)}€</span></div>`
        : `<div class="preis">${angebot.preis.toFixed(2)}€</div>`;
    } else if (angebot.quelle === 'rewe') {
      badgeHtml = '<span class="rewe-online-badge">REWE Online</span>';
      preisHtml = `<div class="preis normal">${angebot.preis.toFixed(2)}€</div>`;
    } else {
      badgeHtml = '<span class="normalpreis-badge">Normalpreis</span>';
      preisHtml = `<div class="preis normal">${angebot.preis.toFixed(2)}€</div>`;
    }
    const bildHtml = angebot.bild_url
      ? `<img class="produkt-bild" src="${angebot.bild_url}" alt="${angebot.produkt}" loading="lazy" onerror="this.style.display='none'">`
      : '';
    const inListe = einkaufItems.has(`${angebot.produkt}|${angebot.haendler}|${aktuellePlz}`);
    const mehrePlz = aktuellePlz.includes(',');
    const plzBadge = mehrePlz && angebot.plz_liste?.length
      ? `<div class="gueltigkeit">PLZ: ${angebot.plz_liste.join(' · ')}</div>` : '';
    return `
      <div class="ergebnis-karte" style="position:relative;">
        ${quellBadgeHtml(angebot.quelle)}
        ${bildHtml}
        <div class="haendler ${haendlerKlasse}">${angebot.haendler}</div>
        <div class="produkt-info">
          <div class="produkt-name">${angebot.produkt}</div>
          <div class="beschreibung">${angebot.beschreibung}</div>
          ${angebot.kategorie ? `<div class="gueltigkeit">${angebot.kategorie}</div>` : ''}
          ${vonDatum ? `<div class="gueltigkeit">${vonDatum} – ${bisDatum}</div>` : ''}
          ${plzBadge}
        </div>
        <div class="preis-bereich">
          ${preisHtml}
          ${badgeHtml}
          <button class="add-to-list-btn${inListe ? ' hinzugefuegt' : ''}"
            onclick="addToEinkaufsliste('${angebot.produkt.replace(/'/g,"\\'")}','${angebot.haendler.replace(/'/g,"\\'")}',${angebot.preis},'${aktuellePlz}',this)"
            ${inListe ? 'disabled' : ''}>
            ${inListe ? 'Hinzugefügt' : '+ Einkaufsliste'}
          </button>
        </div>
      </div>`;
  }

  if (exakt.length === 0 && weiteres.length > 0) {
    html += '<p class="status" style="margin-bottom:8px;">Keine exakten Treffer — ähnliche Produkte:</p>';
  }

  exakt.forEach(a => { html += karteHtml(a); });

  if (exakt.length > 0 && weiteres.length > 0) {
    html += `<div class="weiteres-trenner">Weitere Produkte mit „${aktuellerSuchbegriff}"</div>`;
    weiteres.forEach(a => { html += karteHtml(a); });
  } else if (exakt.length === 0) {
    weiteres.forEach(a => { html += karteHtml(a); });
  }

  document.getElementById('ergebnisse').innerHTML = html;
}

// ── Merkliste ─────────────────────────────────────────────────────────────────
const API = 'https://mercado-app019.onrender.com';
let merklisteItems = new Set(); // "suchbegriff|plz"

function getUsername() {
  return localStorage.getItem('mercado_username');
}

let gewaehlterAvatar = '🍎';

function waehleAvatar(btn, emoji) {
  gewaehlterAvatar = emoji;
  document.querySelectorAll('.avatar-option').forEach(b => b.classList.remove('ausgewaehlt'));
  btn.classList.add('ausgewaehlt');
}

function speichereUsername() {
  const input = document.getElementById('username-input').value.trim();
  if (!input) return;
  localStorage.setItem('mercado_username', input);
  localStorage.setItem('mercado_avatar', gewaehlterAvatar);
  document.getElementById('username-modal').style.display = 'none';
  fetch(`${API}/users/register?username=${encodeURIComponent(input)}`, { method: 'POST' }).catch(() => {});
  zeigeAvatar();
  ladeMerkliste();
  zeigeZuletztKarussell();
}

function zeigeAvatar() {
  const username = getUsername();
  if (!username) return;
  const avatar = localStorage.getItem('mercado_avatar') || '🍎';
  document.getElementById('avatar-bubble').textContent  = avatar;
  document.getElementById('avatar-tooltip').textContent = username;
  document.getElementById('avatar-menu-name').textContent = username;
  document.getElementById('avatar-container').style.display = 'block';
}

function toggleAvatarMenu() {
  const menu = document.getElementById('avatar-menu');
  menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

function ausloggen() {
  localStorage.removeItem('mercado_username');
  localStorage.removeItem('mercado_avatar');
  merklisteItems = new Set();
  gewaehlterAvatar = '🍎';
  document.getElementById('avatar-container').style.display = 'none';
  document.getElementById('avatar-menu').style.display = 'none';
  document.getElementById('username-input').value = '';
  document.querySelectorAll('.avatar-option').forEach(b => b.classList.remove('ausgewaehlt'));
  document.getElementById('username-modal').style.display = 'flex';
  goHome();
}

// Close avatar menu when clicking outside
document.addEventListener('click', e => {
  if (!e.target.closest('.avatar-container')) {
    const menu = document.getElementById('avatar-menu');
    if (menu) menu.style.display = 'none';
  }
});

async function ladeMerkliste() {
  const username = getUsername();
  if (!username) return;
  try {
    const res = await fetch(`${API}/merkliste/${encodeURIComponent(username)}`);
    const items = await res.json();
    merklisteItems = new Set(items.map(i => `${i.suchbegriff}|${i.plz}`));
    aktualisiereMerkenButton();
  } catch {}
}

async function toggleMerken() {
  const username = getUsername();
  if (!username) { document.getElementById('username-modal').style.display = 'flex'; return; }
  if (!aktuellerSuchbegriff) return;

  const key = `${aktuellerSuchbegriff}|${aktuellePlz}`;
  const warGemerkt = merklisteItems.has(key);

  // Optimistic update
  if (warGemerkt) merklisteItems.delete(key); else merklisteItems.add(key);
  aktualisiereMerkenButton();

  try {
    const params = `suchbegriff=${encodeURIComponent(aktuellerSuchbegriff)}&plz=${encodeURIComponent(aktuellePlz)}`;
    const res = await fetch(
      `${API}/merkliste/${encodeURIComponent(username)}?${params}`,
      { method: warGemerkt ? 'DELETE' : 'POST' }
    );
    if (!res.ok) throw new Error();
  } catch {
    if (warGemerkt) merklisteItems.add(key); else merklisteItems.delete(key);
    aktualisiereMerkenButton();
  }
}

function aktualisiereMerkenButton() {
  const btn = document.getElementById('merken-btn');
  if (!btn || !aktuellerSuchbegriff) return;
  const gemerkt = merklisteItems.has(`${aktuellerSuchbegriff}|${aktuellePlz}`);
  btn.textContent = gemerkt ? 'Gemerkt' : 'Merken';
  btn.classList.toggle('gemerkt', gemerkt);
}

async function zeigeWunschliste(pushState = true) {
  const username = getUsername();
  if (!username) { document.getElementById('username-modal').style.display = 'flex'; return; }

  if (pushState) updateURL({ view: 'wishlist' });

  const section = document.getElementById('wunschliste-section');
  document.getElementById('wunschliste-username').textContent = username;
  section.style.display = 'block';
  section.scrollIntoView({ behavior: 'smooth' });

  const inhalt = document.getElementById('wunschliste-inhalt');
  inhalt.innerHTML = '<p class="status">Lade gespeicherte Suchen...</p>';

  try {
    const res   = await fetch(`${API}/merkliste/${encodeURIComponent(username)}`);
    const items = await res.json();

    if (items.length === 0) {
      inhalt.innerHTML = '<p class="status">Noch keine Suchen gespeichert. Suche etwas und klick auf Merken.</p>';
      return;
    }

    inhalt.innerHTML = '';

    // Fetch results for each saved search in parallel
    await Promise.all(items.map(async item => {
      const gruppe = document.createElement('div');
      gruppe.className = 'merkliste-gruppe';
      gruppe.innerHTML = `
        <div class="merkliste-gruppe-header" onclick="toggleGruppe(this)">
          <span class="gruppe-arrow">▾</span>
          <span class="merkliste-suche-titel">${item.suchbegriff}</span>
          <span class="plz-badge">${item.plz}</span>
          <button class="merkliste-remove-btn" onclick="event.stopPropagation(); entferneVonMerkliste('${item.suchbegriff.replace(/'/g,"\\'")}','${item.plz}',this)">✕</button>
        </div>
        <div class="merkliste-ergebnisse">
          <p class="status">Lade...</p>
        </div>`;
      inhalt.appendChild(gruppe);

      try {
        const r = await fetch(`${API}/search?q=${encodeURIComponent(item.suchbegriff)}&plz=${encodeURIComponent(item.plz)}`);
        const d = await r.json();
        const container = gruppe.querySelector('.merkliste-ergebnisse');

        if (!d.ergebnisse?.length) {
          container.innerHTML = '<p class="status" style="font-size:13px;">Keine aktuellen Angebote.</p>';
          return;
        }

        container.innerHTML = d.ergebnisse.map(a => {
          const haendlerKlasse = 'haendler-' + a.haendler.toLowerCase().replace(/\s+/g,'');
          const preisHtml = a.ist_angebot && a.alter_preis
            ? `<div class="preis">${a.preis?.toFixed(2)}€ <span class="statt-preis">statt ${a.alter_preis.toFixed(2)}€</span></div>`
            : `<div class="preis ${a.ist_angebot ? '' : 'normal'}">${a.preis?.toFixed(2)}€</div>`;
          const badge = a.ist_angebot
            ? '<span class="angebot-badge">Angebot</span>'
            : '<span class="normalpreis-badge">Normalpreis</span>';
          return `
            <div class="ergebnis-karte kompakt">
              <div class="haendler ${haendlerKlasse}">${a.haendler}</div>
              <div class="produkt-info">
                <div class="produkt-name">${a.produkt}</div>
                ${a.gueltig_bis ? `<div class="gueltigkeit">bis ${new Date(a.gueltig_bis).toLocaleDateString('de-DE')}</div>` : ''}
              </div>
              <div class="preis-bereich">
                ${preisHtml}${badge}
                <button class="add-to-list-btn${einkaufItems.has(`${a.produkt}|${a.haendler}|${item.plz}`) ? ' hinzugefuegt' : ''}"
                  onclick="addToEinkaufsliste('${(a.produkt||'').replace(/'/g,"\\'")}','${a.haendler.replace(/'/g,"\\'")}',${a.preis},'${item.plz}',this)"
                  ${einkaufItems.has(`${a.produkt}|${a.haendler}|${item.plz}`) ? 'disabled' : ''}>
                  ${einkaufItems.has(`${a.produkt}|${a.haendler}|${item.plz}`) ? 'Hinzugefügt' : '+ Einkaufsliste'}
                </button>
              </div>
            </div>`;
        }).join('');
      } catch {
        gruppe.querySelector('.merkliste-ergebnisse').innerHTML = '<p class="status">Fehler beim Laden</p>';
      }
    }));
  } catch {
    inhalt.innerHTML = '<p class="status">Fehler beim Laden.</p>';
  }
}

function toggleGruppe(header) {
  const gruppe = header.closest('.merkliste-gruppe');
  gruppe.classList.toggle('collapsed');
  header.querySelector('.gruppe-arrow').textContent =
    gruppe.classList.contains('collapsed') ? '▸' : '▾';
}

async function entferneVonMerkliste(suchbegriff, plz, btn) {
  const username = getUsername();
  if (!username) return;
  const params = `suchbegriff=${encodeURIComponent(suchbegriff)}&plz=${encodeURIComponent(plz)}`;
  await fetch(`${API}/merkliste/${encodeURIComponent(username)}?${params}`, { method: 'DELETE' });
  merklisteItems.delete(`${suchbegriff}|${plz}`);
  btn.closest('.merkliste-gruppe').remove();
  aktualisiereMerkenButton();
}

function schliesseWunschliste() {
  document.getElementById('wunschliste-section').style.display = 'none';
  if (aktuellerSuchbegriff) {
    updateURL({ q: aktuellerSuchbegriff, plz: aktuellePlz });
  } else {
    history.pushState({}, '', window.location.pathname);
  }
}

// ── Wunschliste Suche ─────────────────────────────────────────────────────────
function filterWunschliste() {
  const term = document.getElementById('wunschliste-suche').value.toLowerCase();
  document.querySelectorAll('#wunschliste-inhalt .merkliste-gruppe').forEach(gruppe => {
    const titel = gruppe.querySelector('.merkliste-suche-titel')?.textContent.toLowerCase() || '';
    gruppe.style.display = titel.includes(term) ? '' : 'none';
  });
}

// ── Einkaufsliste ─────────────────────────────────────────────────────────────
let einkaufItems = new Set(); // "produkt|haendler|plz"

async function addToEinkaufsliste(produkt, haendler, preis, plz, btn) {
  const username = getUsername();
  if (!username) { document.getElementById('username-modal').style.display = 'flex'; return; }

  const key = `${produkt}|${haendler}|${plz}`;
  if (einkaufItems.has(key)) return;

  const params = new URLSearchParams({ produkt_name: produkt, haendler, preis, plz });
  try {
    const res = await fetch(`${API}/einkaufsliste/${encodeURIComponent(username)}?${params}`, { method: 'POST' });
    if (res.ok) {
      einkaufItems.add(key);
      if (btn) { btn.textContent = 'Hinzugefügt'; btn.classList.add('hinzugefuegt'); btn.disabled = true; }
    }
  } catch {}
}

async function ladeEinkaufsliste() {
  const username = getUsername();
  if (!username) return;
  try {
    const res = await fetch(`${API}/einkaufsliste/${encodeURIComponent(username)}`);
    const items = await res.json();
    einkaufItems = new Set(items.map(i => `${i.produkt_name}|${i.haendler}|${i.plz}`));
  } catch {}
}

async function zeigeEinkaufsliste() {
  const username = getUsername();
  if (!username) { document.getElementById('username-modal').style.display = 'flex'; return; }

  document.getElementById('einkaufsliste-username').textContent = username;
  const section = document.getElementById('einkaufsliste-section');
  section.style.display = 'block';
  section.scrollIntoView({ behavior: 'smooth' });

  const inhalt = document.getElementById('einkaufsliste-inhalt');
  inhalt.innerHTML = '<p class="status">Lade Einkaufsliste...</p>';

  try {
    const res = await fetch(`${API}/einkaufsliste/${encodeURIComponent(username)}`);
    const items = await res.json();

    if (items.length === 0) {
      inhalt.innerHTML = '<p class="status">Die Einkaufsliste ist leer. Füge Produkte über die Suchergebnisse hinzu.</p>';
      return;
    }

    inhalt.innerHTML = items.map(item => `
      <div class="einkauf-item" data-name="${item.produkt_name.toLowerCase()}" data-haendler="${item.haendler.toLowerCase()}">
        <div class="einkauf-item-info">
          <div class="einkauf-item-name">${item.produkt_name}</div>
          <div class="einkauf-item-meta">${item.haendler} · ${item.preis?.toFixed(2)}€ · PLZ ${item.plz}</div>
        </div>
        <button class="merkliste-remove-btn" onclick="entferneVonEinkaufsliste(${item.id}, '${item.produkt_name.replace(/'/g,"\\'")}','${item.haendler.replace(/'/g,"\\'")}','${item.plz}', this)">✕</button>
      </div>
    `).join('');
  } catch {
    inhalt.innerHTML = '<p class="status">Fehler beim Laden.</p>';
  }
}

function schliesseEinkaufsliste() {
  document.getElementById('einkaufsliste-section').style.display = 'none';
}

async function entferneVonEinkaufsliste(id, produkt, haendler, plz, btn) {
  const username = getUsername();
  if (!username) return;
  try {
    await fetch(`${API}/einkaufsliste/${encodeURIComponent(username)}/${id}`, { method: 'DELETE' });
    einkaufItems.delete(`${produkt}|${haendler}|${plz}`);
    btn.closest('.einkauf-item').remove();
    renderErgebnisse();
  } catch {}
}

function filterEinkaufsliste() {
  const term = document.getElementById('einkaufsliste-suche').value.toLowerCase();
  document.querySelectorAll('#einkaufsliste-inhalt .einkauf-item').forEach(item => {
    const text = (item.dataset.name + ' ' + item.dataset.haendler);
    item.style.display = text.includes(term) ? '' : 'none';
  });
}

// ── URL state ─────────────────────────────────────────────────────────────────
function updateURL(params) {
  const url = new URL(window.location.href);
  url.search = '';
  Object.entries(params).forEach(([k, v]) => { if (v) url.searchParams.set(k, v); });
  history.pushState(params, '', url);
}

function goHome() {
  history.pushState({}, '', window.location.pathname);
  document.getElementById('ergebnisse').innerHTML = '';
  document.getElementById('filter-bar').style.display = 'none';
  document.getElementById('wunschliste-section').style.display = 'none';
  document.getElementById('suchbegriff').value = '';
  schliesseVerlauf();
  alleErgebnisse = [];
  aktuellerSuchbegriff = '';
  zeigeZuletztKarussell();
}

// ── Zuletzt gesucht ───────────────────────────────────────────────────────────
const ZULETZT_MAX = 8;

function zuletztKey() {
  const username = getUsername();
  return username ? `mercado_zuletzt_${username}` : null;
}

function ladeZuletztGesucht() {
  const key = zuletztKey();
  if (!key) return [];
  try { return JSON.parse(localStorage.getItem(key)) || []; }
  catch { return []; }
}

function speichereZuletztGesucht(q, plz) {
  const key = zuletztKey();
  if (!key) return;
  let liste = ladeZuletztGesucht().filter(e => !(e.q === q && e.plz === plz));
  liste.unshift({ q, plz });
  if (liste.length > ZULETZT_MAX) liste = liste.slice(0, ZULETZT_MAX);
  localStorage.setItem(key, JSON.stringify(liste));
}

function entferneZuletzt(index) {
  const key = zuletztKey();
  if (!key) return;
  const liste = ladeZuletztGesucht();
  liste.splice(index, 1);
  localStorage.setItem(key, JSON.stringify(liste));
  zeigeZuletztKarussell();
}

function loescheAlleZuletzt() {
  const key = zuletztKey();
  if (key) localStorage.removeItem(key);
  zeigeZuletztKarussell();
}

function sucheMitZuletzt(q, plz) {
  document.getElementById('suchbegriff').value = q;
  document.getElementById('plz').value = plz;
  suchen();
}

function scrollZuletzt(dir) {
  const track = document.getElementById('zuletzt-track');
  if (track) track.scrollBy({ left: dir * 160, behavior: 'smooth' });
}

function zeigeZuletztKarussell() {
  const section = document.getElementById('zuletzt-section');
  const liste = ladeZuletztGesucht();

  if (liste.length === 0) { section.style.display = 'none'; return; }

  const tilesHtml = liste.map((e, i) => `
    <div class="zuletzt-kachel" onclick="sucheMitZuletzt('${e.q.replace(/'/g, "\\'")}', '${e.plz}')">
      <button class="zuletzt-remove" onclick="event.stopPropagation(); entferneZuletzt(${i})">✕</button>
      <div class="zuletzt-icon">🔍</div>
      <div class="zuletzt-name">${e.q}</div>
      <div class="zuletzt-plz">${e.plz}</div>
    </div>
  `).join('');

  section.innerHTML = `
    <div class="zuletzt-header">
      <span class="zuletzt-titel">Zuletzt gesucht</span>
      <button class="zuletzt-clear-btn" onclick="loescheAlleZuletzt()">Alle löschen</button>
    </div>
    <div class="zuletzt-wrapper">
      <button class="zuletzt-arrow" onclick="scrollZuletzt(-1)">‹</button>
      <div class="zuletzt-track" id="zuletzt-track">${tilesHtml}</div>
      <button class="zuletzt-arrow" onclick="scrollZuletzt(1)">›</button>
    </div>
  `;
  section.style.display = 'block';
}

// ── Autocomplete ──────────────────────────────────────────────────────────────
let aktiverVorschlagIndex = -1;
let vorschlagDebounce = null;

function levenshtein(a, b) {
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, (_, i) => Array.from({ length: n + 1 }, (_, j) => i === 0 ? j : j === 0 ? i : 0));
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = a[i-1] === b[j-1] ? dp[i-1][j-1] : 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
  return dp[m][n];
}

async function findeAehnliche(q) {
  try {
    const res = await fetch(`${API}/suggest?q=${encodeURIComponent(q.slice(0, 4))}`);
    const kandidaten = await res.json();
    return kandidaten
      .map(p => ({ p, dist: levenshtein(q.toLowerCase(), p.toLowerCase().slice(0, q.length + 2)) }))
      .filter(x => x.dist <= 2)
      .sort((a, b) => a.dist - b.dist)
      .slice(0, 3)
      .map(x => x.p);
  } catch { return []; }
}

function zeigeVorschlaege() {
  clearTimeout(vorschlagDebounce);
  vorschlagDebounce = setTimeout(async () => {
    const q = document.getElementById('suchbegriff').value.trim();
    const container = document.getElementById('vorschlaege');
    aktiverVorschlagIndex = -1;

    if (q.length < 2) { container.style.display = 'none'; return; }

    try {
      const res = await fetch(`${API}/suggest?q=${encodeURIComponent(q)}`);
      const vorschlaege = await res.json();

      if (vorschlaege.length === 0) { container.style.display = 'none'; return; }

      container.innerHTML = vorschlaege.map(v => {
        const idx = v.toLowerCase().indexOf(q.toLowerCase());
        const highlighted = idx >= 0
          ? v.slice(0, idx) + `<span class="vorschlag-highlight">${v.slice(idx, idx + q.length)}</span>` + v.slice(idx + q.length)
          : v;
        return `<div class="vorschlag-item" onmousedown="waehleVorschlag('${v.replace(/'/g, "\\'")}')">${highlighted}</div>`;
      }).join('');
      container.style.display = 'block';
    } catch {
      container.style.display = 'none';
    }
  }, 200);
}

function navigiereVorschlaege(e) {
  const items = document.querySelectorAll('.vorschlag-item');
  if (!items.length) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    aktiverVorschlagIndex = Math.min(aktiverVorschlagIndex + 1, items.length - 1);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    aktiverVorschlagIndex = Math.max(aktiverVorschlagIndex - 1, -1);
  } else if (e.key === 'Escape') {
    schliesseVorschlaege();
    return;
  } else {
    return;
  }

  items.forEach((el, i) => el.classList.toggle('aktiv', i === aktiverVorschlagIndex));
  if (aktiverVorschlagIndex >= 0) {
    document.getElementById('suchbegriff').value = items[aktiverVorschlagIndex].textContent;
  }
}

function waehleVorschlag(v) {
  document.getElementById('suchbegriff').value = v;
  schliesseVorschlaege();
  suchen();
}

function schliesseVorschlaege() {
  document.getElementById('vorschlaege').style.display = 'none';
  aktiverVorschlagIndex = -1;
}

// ── Search ────────────────────────────────────────────────────────────────────
async function suchen(pushState = true) {
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
  ergebnisseDiv.innerHTML = '<p class="status">Suche läuft...</p>';
  document.getElementById('filter-bar').style.display = 'none';
  document.getElementById('zuletzt-section').style.display = 'none';
  schliesseVerlauf();

  try {
    const antwort = await fetch(`${API}/search?q=${encodeURIComponent(suchbegriff)}&plz=${plz}`);
    const daten   = await antwort.json();

    if (daten.anzahl === 0) {
      const aehnliche = await findeAehnliche(suchbegriff);
      const vorschlagHtml = aehnliche.length
        ? `<p class="status" style="margin-top:8px;">Meinten Sie: ${aehnliche.map(v =>
            `<button class="vorschlag-link-btn" onclick="waehleVorschlag('${v.replace(/'/g, "\\'")}')">${v}</button>`
          ).join('')}?</p>`
        : '';
      ergebnisseDiv.innerHTML = `<p class="status">Keine Angebote gefunden. Versuche einen anderen Suchbegriff.</p>${vorschlagHtml}`;
      return;
    }

    alleErgebnisse       = daten.ergebnisse;
    aktuellerSuchbegriff = suchbegriff;
    aktuellePlz          = plz;
    speichereZuletztGesucht(suchbegriff, plz);
    aktiverHaendler      = null;
    aktiveKategorie      = null;
    nurAngebote          = false;
    aktiveSortierung     = 'preis-asc';

    if (pushState) updateURL({ q: suchbegriff, plz });
    zeigeFilterBar();
    renderErgebnisse();

  } catch {
    ergebnisseDiv.innerHTML = '<p class="status">Fehler: Ist der Backend Server gestartet?</p>';
  } finally {
    button.disabled    = false;
    button.textContent = 'Suchen';
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async function() {
  const suchfeld = document.getElementById('suchbegriff');
  if (suchfeld) {
    suchfeld.addEventListener('input', zeigeVorschlaege);
    suchfeld.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        schliesseVorschlaege();
        suchen();
      } else {
        navigiereVorschlaege(e);
      }
    });
    suchfeld.addEventListener('blur', () => setTimeout(schliesseVorschlaege, 150));
  }
  document.getElementById('plz')?.addEventListener('keydown', e => { if (e.key === 'Enter') suchen(); });

  document.getElementById('username-input')
    ?.addEventListener('keydown', e => { if (e.key === 'Enter') speichereUsername(); });

  if (!getUsername()) {
    document.getElementById('username-modal').style.display = 'flex';
  } else {
    zeigeAvatar();
    await ladeMerkliste();
    await ladeEinkaufsliste();
  }

  zeigeZuletztKarussell();

  // Restore state from URL
  const params   = new URLSearchParams(window.location.search);
  const qParam   = params.get('q');
  const plzParam = params.get('plz');
  const view     = params.get('view');

  if (view === 'wishlist') {
    zeigeWunschliste(false);
  } else if (qParam) {
    document.getElementById('suchbegriff').value = qParam;
    if (plzParam) document.getElementById('plz').value = plzParam;
    suchen(false);
  }

  // Browser back/forward
  window.addEventListener('popstate', async () => {
    const p    = new URLSearchParams(window.location.search);
    const q    = p.get('q');
    const view = p.get('view');
    if (view === 'wishlist') {
      zeigeWunschliste(false);
    } else if (q) {
      document.getElementById('suchbegriff').value = q;
      document.getElementById('plz').value = p.get('plz') || '72555';
      suchen(false);
    } else {
      document.getElementById('ergebnisse').innerHTML = '';
      document.getElementById('filter-bar').style.display = 'none';
      document.getElementById('wunschliste-section').style.display = 'none';
      schliesseVerlauf();
      alleErgebnisse = [];
      aktuellerSuchbegriff = '';
      zeigeZuletztKarussell();
    }
  });
});
