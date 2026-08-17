(function () {
  const nav = document.getElementById('top-nav');
  const searchWrap = nav.querySelector('.search-wrap');
  const searchInput = document.getElementById('link-search');
  const searchToggle = document.getElementById('search-toggle');
  const sectionsWrap = nav.querySelector('.sections-wrap');
  const sectionsToggle = document.getElementById('sections-toggle');
  const sectionsMenu = document.getElementById('sections-menu');
  const main = document.getElementById('main-content');

  function setSearchOpen(open) {
    searchWrap.classList.toggle('is-open', open);
    searchToggle.setAttribute('aria-expanded', String(open));
    if (open) {
      searchInput.focus();
    }
  }

  function setSectionsOpen(open) {
    sectionsMenu.hidden = !open;
    sectionsToggle.setAttribute('aria-expanded', String(open));
  }

  searchToggle.addEventListener('click', () => {
    const willOpen = !searchWrap.classList.contains('is-open');
    setSearchOpen(willOpen);
    setSectionsOpen(false);
  });

  sectionsToggle.addEventListener('click', () => {
    const willOpen = sectionsMenu.hidden;
    setSectionsOpen(willOpen);
    setSearchOpen(false);
  });

  sectionsMenu.addEventListener('click', (e) => {
    if (e.target.tagName === 'A') setSectionsOpen(false);
  });

  document.addEventListener('click', (e) => {
    if (!nav.contains(e.target)) {
      setSectionsOpen(false);
    }
  });

  nav.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      setSearchOpen(false);
      setSectionsOpen(false);
    }
  });

  searchInput.addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    const items = main.querySelectorAll('[data-search]');
    items.forEach((el) => {
      const match = !q || el.dataset.search.includes(q);
      el.style.display = match ? '' : 'none';
    });

    const sections = main.querySelectorAll('[data-section]');
    sections.forEach((sec) => {
      const sectionItems = sec.querySelectorAll('[data-search]');
      const anyVisible = sectionItems.length === 0 ||
        Array.from(sectionItems).some((el) => el.style.display !== 'none');
      sec.style.display = q && !anyVisible ? 'none' : '';
      if (q && sec.tagName === 'DETAILS') sec.open = true;
    });
  });
})();
