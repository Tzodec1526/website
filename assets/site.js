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

  function init() {
    initPrintButtons();
    initReveals();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
