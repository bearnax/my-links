(function () {
  var root = document.documentElement;
  var main = document.getElementById('main-content');
  var searchInput = document.getElementById('link-search');
  var sectionsToggle = document.getElementById('sections-toggle');
  var sectionsMenu = document.getElementById('sections-menu');
  var themeToggle = document.getElementById('theme-toggle');
  var emptyState = document.getElementById('empty-state');
  var favoritesRow = document.getElementById('favorites-row');
  var sectionsContainer = document.getElementById('sections-container');

  /* Theme */

  var stored = null;
  try { stored = localStorage.getItem('wl-theme'); } catch (e) {}
  root.setAttribute('data-theme', stored || 'light');

  themeToggle.addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('wl-theme', next); } catch (e) {}
  });

  /* Rendering */

  function faviconUrl(url) {
    try { return 'https://www.google.com/s2/favicons?sz=64&domain=' + new URL(url).hostname; }
    catch (e) { return ''; }
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    for (var key in attrs) {
      if (key === 'text') node.textContent = attrs[key];
      else node.setAttribute(key, attrs[key]);
    }
    (children || []).forEach(function (child) { node.appendChild(child); });
    return node;
  }

  function renderFavorite(fav) {
    var a = el('a', { class: 'favorite-link', href: fav.url, 'data-search': fav.search || fav.label.toLowerCase() });
    a.appendChild(el('img', { src: faviconUrl(fav.url), alt: '' }));
    a.appendChild(document.createTextNode(fav.label));
    return a;
  }

  function renderLinkRow(link) {
    var a = el('a', { class: 'row-link', href: link.url, 'data-search': link.search || link.label.toLowerCase() });
    a.appendChild(el('img', { src: faviconUrl(link.url), alt: '' }));
    a.appendChild(el('span', { class: 'row-label', text: link.label }));
    a.appendChild(el('span', { class: 'row-arrow', text: '↗' }));
    return a;
  }

  function renderProject(project) {
    var name = project.emoji ? project.emoji + ' ' + project.name : project.name;
    var nameSpan = el('span', { class: 'project-name' }, [document.createTextNode(name)]);
    if (project.note) {
      nameSpan.appendChild(document.createTextNode(' '));
      nameSpan.appendChild(el('span', { class: 'project-note', text: project.note }));
    }

    var statusSpan = el('span', { class: 'project-status' }, [
      el('span', { class: 'dot dot-' + project.status }),
      document.createTextNode(project.statusLabel)
    ]);

    var info = el('div', { class: 'project-info' }, [nameSpan, statusSpan]);

    var live = project.live
      ? el('a', { class: 'pl pl-live', href: project.live, text: 'Live' })
      : el('span', { class: 'pl pl-off', text: 'Live' });
    var repo = project.repo
      ? el('a', { class: 'pl', href: project.repo, text: 'Repo' })
      : el('span', { class: 'pl pl-off', text: 'Repo' });
    var links = el('div', { class: 'project-links' }, [live, repo]);

    return el('div', { class: 'project', 'data-search': project.search || project.name.toLowerCase() }, [info, links]);
  }

  function renderSection(section, index) {
    var num = String(index + 1).padStart(2, '0');
    var summary = el('summary', {}, [
      el('span', { class: 'sec-num', text: num }),
      el('span', { class: 'sec-title', text: section.title }),
      el('span', { class: 'sec-rule' }),
      el('span', { class: 'sec-count' }),
      el('span', { class: 'sec-glyph' })
    ]);

    var listClass = section.type === 'projects' ? 'project-list' : 'link-list';
    var items = (section.type === 'projects' ? section.projects : section.links)
      .map(section.type === 'projects' ? renderProject : renderLinkRow);
    var list = el('div', { class: listClass }, items);

    var details = el('details', { id: section.id, class: 'section-panel', 'data-section': '', 'data-num': num });
    if (section.open) details.setAttribute('open', '');
    details.appendChild(summary);
    details.appendChild(list);
    return details;
  }

  function renderSectionsMenuLink(section) {
    return el('a', { href: '#' + section.id, text: section.title });
  }

  function render(data) {
    (data.favorites || []).forEach(function (fav) {
      favoritesRow.appendChild(renderFavorite(fav));
    });

    (data.sections || []).forEach(function (section, index) {
      sectionsContainer.appendChild(renderSection(section, index));
      sectionsMenu.appendChild(renderSectionsMenuLink(section));
    });
  }

  fetch('data/links.json')
    .then(function (res) { return res.json(); })
    .then(function (data) {
      render(data);
      initInteractions();
    })
    .catch(function (err) {
      console.error('Failed to load links data', err);
    });

  /* Interactions (search, sections menu, link counts) — wired after render */

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
