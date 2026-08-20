/* Behaviour over the markup Eleventy already rendered from data/links.json
   (see src/_includes/cards.njk).

   Two things live here: remembering which sections the reader left open, and
   nothing else. The +/- glyph is pure CSS off the <details> open state, and
   the page's colour is chosen by the inline script in the head so it is
   settled before first paint. */

(function () {
  var STORE_KEY = 'wl-open-sections';

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
