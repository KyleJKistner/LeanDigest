'use strict';
(() => {
  const cards = Array.from(document.querySelectorAll('.card[data-search]'));
  const search = document.getElementById('search');
  const coverage = document.getElementById('coverage');
  const subject = document.getElementById('subject');
  if (search && coverage && subject) {
    const norm = s => s.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
    const indexed = cards.map(card => [card, norm(card.dataset.search)]);
    const params = new URLSearchParams(location.hash.slice(1));
    search.value = params.get('q') || '';
    if (['documented', 'readings', 'all'].includes(params.get('coverage'))) coverage.value = params.get('coverage');
    if (Array.from(subject.options).some(x => x.value === params.get('subject'))) subject.value = params.get('subject');
    const apply = () => {
      const query = norm(search.value).trim().split(/\s+/).filter(Boolean);
      let count = 0;
      for (const [card, haystack] of indexed) {
        const ok = query.every(term => haystack.includes(term)) &&
          (coverage.value === 'all' || (coverage.value === 'readings' ? card.dataset.readers === 'true' : card.dataset.documented === 'true')) &&
          (!subject.value || card.dataset.subject === subject.value);
        card.hidden = !ok; count += Number(ok);
      }
      document.getElementById('result-count').textContent = `${count} of ${cards.length} findings shown`;
      document.getElementById('empty').hidden = count !== 0;
      const next = new URLSearchParams();
      if (search.value) next.set('q', search.value);
      if (coverage.value !== 'documented') next.set('coverage', coverage.value);
      if (subject.value) next.set('subject', subject.value);
      try { history.replaceState(null, '', location.pathname + location.search + (next.toString() ? '#' + next : '')); } catch (_) {}
    };
    search.addEventListener('input', apply); coverage.addEventListener('change', apply); subject.addEventListener('change', apply);
    document.querySelector('form').addEventListener('submit', e => { e.preventDefault(); apply(); }); apply();
  }
  if (window.katex) {
    document.querySelectorAll('[data-tex]').forEach(node => {
      try {
        window.katex.render(node.dataset.tex, node, {output:'mathml', displayMode:node.dataset.display === 'true',
          throwOnError:false, strict:'ignore', trust:false, maxExpand:1000, maxSize:20});
      } catch (_) { /* Retain literal source TeX when unsupported. */ }
    });
  }
})();
