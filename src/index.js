(function () {
  var root = document.documentElement;
  var main = document.getElementById('main-content');
  var searchInput = document.getElementById('link-search');
  var sectionsToggle = document.getElementById('sections-toggle');
  var sectionsMenu = document.getElementById('sections-menu');
  var themeToggle = document.getElementById('theme-toggle');
  var emptyState = document.getElementById('empty-state');

  /* Theme */

  var stored = null;
  try { stored = localStorage.getItem('wl-theme'); } catch (e) {}
  root.setAttribute('data-theme', stored || 'light');

  themeToggle.addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('wl-theme', next); } catch (e) {}
  });

  /* Interactions (search, sections menu, link counts).

     The cards themselves are rendered at build time by Eleventy from
     data/links.json — see src/_includes/cards.njk. This file only wires up
     behaviour over the markup that is already in the document. */

  initInteractions();

  function initInteractions() {
    var panels = Array.prototype.slice.call(document.querySelectorAll('.section-panel'));

    function setSectionsOpen(open) {
      sectionsMenu.hidden = !open;
      sectionsToggle.setAttribute('aria-expanded', String(open));
    }

    sectionsToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      setSectionsOpen(sectionsMenu.hidden);
    });

    sectionsMenu.addEventListener('click', function (e) {
      if (e.target.tagName !== 'A') return;
      var target = document.querySelector(e.target.getAttribute('href'));
      if (target) target.open = true;
      setSectionsOpen(false);
    });

    document.addEventListener('click', function (e) {
      if (!sectionsMenu.parentNode.contains(e.target)) setSectionsOpen(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setSectionsOpen(false);
    });

    panels.forEach(function (panel) {
      var count = panel.querySelectorAll('[data-search]').length;
      var countEl = panel.querySelector('.sec-count');
      if (countEl) countEl.textContent = count === 1 ? '1 link' : count + ' links';
    });

    var restore = new WeakMap();
    panels.forEach(function (p) { restore.set(p, p.open); });

    searchInput.addEventListener('input', function (e) {
      var q = e.target.value.trim().toLowerCase();
      var anyVisible = false;

      main.querySelectorAll('[data-search]').forEach(function (el) {
        var match = !q || el.dataset.search.indexOf(q) !== -1 ||
          el.textContent.toLowerCase().indexOf(q) !== -1;
        el.style.display = match ? '' : 'none';
        if (match) anyVisible = true;
      });

      main.querySelectorAll('[data-section]').forEach(function (sec) {
        var items = sec.querySelectorAll('[data-search]');
        var visible = Array.prototype.some.call(items, function (el) {
          return el.style.display !== 'none';
        });
        sec.style.display = q && !visible ? 'none' : '';
        if (sec.tagName === 'DETAILS') {
          sec.open = q ? visible : restore.get(sec);
        }
      });

      emptyState.hidden = !q || anyVisible;
    });

    panels.forEach(function (panel) {
      panel.addEventListener('toggle', function () {
        if (!searchInput.value.trim()) restore.set(panel, panel.open);
      });
    });
  }
})();
