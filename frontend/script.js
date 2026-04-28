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

  try {
    // Call backend
    const antwort = await fetch(`http://127.0.0.1:8000/search?q=${encodeURIComponent(suchbegriff)}&plz=${plz}`);
    const daten = await antwort.json();

    if (daten.anzahl === 0) {
      ergebnisseDiv.innerHTML = '<p class="status">Keine Angebote gefunden. Versuche einen anderen Suchbegriff.</p>';
      return;
    }

    // Display results
    let html = `<p class="status">${daten.anzahl} Angebote gefunden</p>`;

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
      const angebotBadge = angebot.alter_preis
        ? `<span class="angebot-badge">Angebot</span>`
        : '';

      const alterPreis = angebot.alter_preis
        ? `<div class="alter-preis">statt ${angebot.alter_preis.toFixed(2)}€</div>`
        : '';

      html += `
        <div class="ergebnis-karte">
          <div class="haendler ${haendlerKlasse}">${angebot.haendler}</div>
          <div class="produkt-info">
            <div class="produkt-name">${angebot.produkt}</div>
            <div class="beschreibung">${angebot.beschreibung}</div>
            <div class="gueltigkeit">📅 ${vonDatum} – ${bisDatum}</div>
          </div>
          <div class="preis-bereich">
            <div class="preis">${angebot.preis.toFixed(2)}€</div>
            ${alterPreis}
            ${angebotBadge}
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
