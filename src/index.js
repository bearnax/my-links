/* Behaviour for my-links:
   1. Theme toggle (Light / Dark mode) with persistence
   2. Search modal with keyboard shortcuts ('/' to open, 'Escape' to close)
   3. Accordion section open/close state persistence
*/

(function () {
  var PREFIX = document.body.dataset.storagePrefix || 'links';
  var STORE_KEY = PREFIX + '-open-sections';
  var THEME_KEY = PREFIX + '-theme';

  var root = document.documentElement;

  /* ==========================================================================
     1. Light / Dark Theme Toggle
     ========================================================================== */

  var themeBtn = document.getElementById('theme-toggle-btn');

  function getActiveTheme() {
    return root.getAttribute('data-theme') || 'light';
  }

  function updateThemeUI(theme) {
    if (!themeBtn) return;
    var iconEl = themeBtn.querySelector('.theme-icon');
    var textEl = themeBtn.querySelector('.theme-text');
    if (theme === 'dark') {
      if (iconEl) iconEl.textContent = '☀️';
      if (textEl) textEl.textContent = 'Light';
      themeBtn.setAttribute('title', 'Switch to light mode');
    } else {
      if (iconEl) iconEl.textContent = '🌙';
      if (textEl) textEl.textContent = 'Dark';
      themeBtn.setAttribute('title', 'Switch to dark mode');
    }
  }

  updateThemeUI(getActiveTheme());

  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var current = getActiveTheme();
      var next = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try {
        localStorage.setItem(THEME_KEY, next);
      } catch (e) {}
      updateThemeUI(next);
    });
  }

  /* ==========================================================================
     2. Section Open / Closed State Persistence
     ========================================================================== */

  var panels = Array.prototype.slice.call(document.querySelectorAll('.section-panel'));
  var storedSections = null;
  try {
    storedSections = JSON.parse(localStorage.getItem(STORE_KEY));
  } catch (e) {}

  if (storedSections && typeof storedSections === 'object') {
    panels.forEach(function (panel) {
      if (Object.prototype.hasOwnProperty.call(storedSections, panel.id)) {
        panel.open = !!storedSections[panel.id];
      }
    });
  }

  panels.forEach(function (panel) {
    panel.addEventListener('toggle', function () {
      var state = {};
      panels.forEach(function (p) {
        state[p.id] = p.open;
      });
      try {
        localStorage.setItem(STORE_KEY, JSON.stringify(state));
      } catch (e) {}
    });
  });

  /* ==========================================================================
     3. Search Modal & Indexing
     ========================================================================== */

  var searchModal = document.getElementById('search-modal');
  var searchInput = document.getElementById('search-input');
  var searchResults = document.getElementById('search-results');
  var openSearchBtn = document.getElementById('open-search-btn');
  var closeSearchBtn = document.getElementById('close-search-btn');
  var searchBackdrop = document.getElementById('search-backdrop');

  // Index all cards across sections and favorites
  var searchIndex = [];

  // Index favorites
  var favLinks = document.querySelectorAll('.favorites-row .favorite-btn');
  favLinks.forEach(function (btn) {
    var label = btn.querySelector('.fav-label');
    searchIndex.push({
      title: label ? label.textContent.trim() : btn.textContent.trim(),
      search: (btn.dataset.search || '').toLowerCase(),
      section: 'Favorites',
      links: [{ label: 'Open', url: btn.getAttribute('href') }]
    });
  });

  // Index section items
  var itemCards = document.querySelectorAll('.item-card');
  itemCards.forEach(function (card) {
    var titleEl = card.querySelector('.item-title');
    if (!titleEl) return;
    var title = titleEl.textContent.trim();
    var search = (card.dataset.search || '').toLowerCase();
    var sectionPanel = card.closest('.section-panel');
    var sectionTitle = sectionPanel ? sectionPanel.querySelector('.sec-title').textContent.trim() : '';

    var linkBtns = card.querySelectorAll('.pill-btn');
    var links = [];
    linkBtns.forEach(function (btn) {
      var labelEl = btn.querySelector('.pill-label');
      links.push({
        label: labelEl ? labelEl.textContent.trim() : 'Link',
        url: btn.getAttribute('href')
      });
    });

    searchIndex.push({
      title: title,
      search: search,
      section: sectionTitle,
      links: links
    });
  });

  function openSearch() {
    if (!searchModal) return;
    searchModal.classList.add('is-open');
    searchModal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    if (searchInput) {
      searchInput.value = '';
      searchInput.focus();
    }
    renderSearchResults('');
  }

  function closeSearch() {
    if (!searchModal) return;
    searchModal.classList.remove('is-open');
    searchModal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function renderSearchResults(query) {
    if (!searchResults) return;
    var trimmed = query.trim().toLowerCase();
    if (!trimmed) {
      searchResults.innerHTML = '<div class="search-empty-state">Type to search through all bookmarks...</div>';
      return;
    }

    var matches = searchIndex.filter(function (item) {
      return item.title.toLowerCase().indexOf(trimmed) !== -1 ||
             item.search.indexOf(trimmed) !== -1 ||
             item.section.toLowerCase().indexOf(trimmed) !== -1;
    });

    if (matches.length === 0) {
      searchResults.innerHTML = '<div class="search-empty-state">No links found matching "' + escapeHtml(query) + '"</div>';
      return;
    }

    var html = '';
    matches.forEach(function (item) {
      html += '<div class="search-result-item">';
      html += '  <div class="search-result-info">';
      html += '    <span class="search-result-title">' + escapeHtml(item.title) + '</span>';
      if (item.section) {
        html += '    <span class="search-result-section">' + escapeHtml(item.section) + '</span>';
      }
      html += '  </div>';
      html += '  <div class="search-result-links">';
      item.links.forEach(function (link) {
        html += '    <a class="pill-btn" href="' + escapeHtml(link.url) + '" target="_blank" rel="noopener noreferrer">';
        html += '      <span class="pill-label">' + escapeHtml(link.label) + '</span>';
        html += '      <span class="pill-arrow">↗</span>';
        html += '    </a>';
      });
      html += '  </div>';
      html += '</div>';
    });

    searchResults.innerHTML = html;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  if (openSearchBtn) {
    openSearchBtn.addEventListener('click', openSearch);
  }
  if (closeSearchBtn) {
    closeSearchBtn.addEventListener('click', closeSearch);
  }
  if (searchBackdrop) {
    searchBackdrop.addEventListener('click', closeSearch);
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      renderSearchResults(searchInput.value);
    });
  }

  // Global hotkeys: '/' opens search, 'Escape' closes
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && !searchModal.classList.contains('is-open')) {
      var tag = e.target.tagName.toLowerCase();
      if (tag !== 'input' && tag !== 'textarea' && !e.target.isContentEditable) {
        e.preventDefault();
        openSearch();
      }
    } else if (e.key === 'Escape' && searchModal && searchModal.classList.contains('is-open')) {
      closeSearch();
    }
  });

})();
