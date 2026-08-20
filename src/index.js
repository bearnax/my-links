/* Behaviour over the markup Eleventy already rendered from data/links.json
   (see src/_includes/cards.njk).

   Two things live here: remembering which sections the reader left open, and
   the footer's palette override. The +/- glyph is pure CSS off the <details>
   open state, and the palette itself is applied by the inline script in the
   head so it is settled before first paint — this file only records the
   choice and keeps the buttons in sync. */

(function () {
  var STORE_KEY = 'wl-open-sections';
  var PALETTE_KEY = 'wl-palette';

  /* Palette override */

  var root = document.documentElement;
  var picker = document.getElementById('palette-picker');
  var buttons = Array.prototype.slice.call(
    picker.querySelectorAll('[data-palette-choice]'));

  var savedPalette = null;
  try { savedPalette = localStorage.getItem(PALETTE_KEY); } catch (e) {}

  syncButtons(savedPalette);

  picker.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-palette-choice]');
    if (!btn) return;

    var choice = btn.dataset.paletteChoice;
    try {
      if (choice) localStorage.setItem(PALETTE_KEY, choice);
      else localStorage.removeItem(PALETTE_KEY);
    } catch (err) {}

    /* An empty choice means "go back to random", which only takes effect on
       the next load; the colour already on screen is a fair draw, so leave
       it alone rather than reshuffling under the reader. */
    if (choice) root.setAttribute('data-palette', choice);
    syncButtons(choice || null);
  });

  function syncButtons(active) {
    buttons.forEach(function (btn) {
      var choice = btn.dataset.paletteChoice;
      btn.setAttribute('aria-pressed',
        String(active ? choice === active : choice === ''));
    });
  }

  /* Section open state */

  var panels = Array.prototype.slice.call(document.querySelectorAll('.section-panel'));

  var stored = null;
  try { stored = JSON.parse(localStorage.getItem(STORE_KEY)); } catch (e) {}

  if (stored && typeof stored === 'object') {
    panels.forEach(function (panel) {
      if (Object.prototype.hasOwnProperty.call(stored, panel.id)) {
        panel.open = !!stored[panel.id];
      }
    });
  }

  panels.forEach(function (panel) {
    panel.addEventListener('toggle', function () {
      var state = {};
      panels.forEach(function (p) { state[p.id] = p.open; });
      try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (e) {}
    });
  });
})();
