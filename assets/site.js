(function () {
  var doc = document.documentElement;
  var supportsReveal = 'IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  doc.classList.add('has-js');

  if (supportsReveal) {
    doc.classList.add('js');
  }

  function initPrintButtons() {
    document.querySelectorAll('.btn-print').forEach(function (button) {
      button.addEventListener('click', function () {
        window.print();
      });
    });
  }

  function initReveals() {
    if (!('IntersectionObserver' in window)) return;

    window.setTimeout(function () {
      doc.classList.add('settled');
    }, 3000);

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    document.querySelectorAll('.rvs').forEach(function (element) {
      observer.observe(element);
    });
  }

  function initResourceFilter() {
    var root = document.querySelector('.res-filter');
    if (!root) return;

    var input = document.getElementById('res-q');
    var countEl = document.getElementById('res-count');
    var noResults = document.getElementById('res-noresults');
    var cats = Array.prototype.slice.call(root.querySelectorAll('.res-cat'));
    var cards = Array.prototype.slice.call(document.querySelectorAll('.res-card'));
    var groups = Array.prototype.slice.call(document.querySelectorAll('.res-group'));
    var total = cards.length;
    var activeCat = 'all';

    function apply() {
      var q = (input.value || '').trim().toLowerCase();
      var shown = 0;
      cards.forEach(function (c) {
        var okCat = activeCat === 'all' || c.getAttribute('data-group') === activeCat;
        var okText = !q || (c.getAttribute('data-text') || '').indexOf(q) !== -1;
        var visible = okCat && okText;
        c.classList.toggle('is-hidden', !visible);
        if (visible) shown++;
      });
      groups.forEach(function (g) {
        g.classList.toggle('is-hidden', !g.querySelector('.res-card:not(.is-hidden)'));
      });
      if (noResults) noResults.hidden = shown !== 0;
      if (countEl) countEl.textContent = (q || activeCat !== 'all') ? ('Showing ' + shown + ' of ' + total) : '';
    }

    function setCat(cat) {
      activeCat = cat;
      cats.forEach(function (b) {
        var on = b.getAttribute('data-cat') === cat;
        b.classList.toggle('is-active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      apply();
    }

    if (input) input.addEventListener('input', apply);
    cats.forEach(function (btn) {
      btn.addEventListener('click', function () { setCat(btn.getAttribute('data-cat')); });
    });
    document.querySelectorAll('.res-reset').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (input) input.value = '';
        setCat('all');
        if (input) input.focus();
      });
    });
  }

  function init() {
    initPrintButtons();
    initReveals();
    initResourceFilter();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
