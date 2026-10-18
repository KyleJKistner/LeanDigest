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
  const gapSearch = document.getElementById('gap-search');
  const gapHead = document.getElementById('gap-head');
  if (gapSearch && gapHead) {
    const norm = s => s.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const rows = Array.from(document.querySelectorAll('.gap-reading')).map(row => ({
      row, search: norm(row.dataset.search), groups: JSON.parse(row.dataset.groups),
      count: Number(row.dataset.count), first: row.dataset.first
    }));
    const restore = () => {
      const params = new URLSearchParams(location.search);
      gapSearch.value = params.get('q') || '';
      gapHead.value = Array.from(gapHead.options).some(x => x.value === params.get('head')) ? params.get('head') : '';
    };
    const apply = (persist = true) => {
      const terms = norm(gapSearch.value).trim().split(/\s+/).filter(Boolean);
      let proofs = 0, gaps = 0;
      for (const item of rows) {
        const group = gapHead.value && Object.prototype.hasOwnProperty.call(item.groups, gapHead.value)
          ? item.groups[gapHead.value] : null;
        const count = gapHead.value ? (group ? group.count : 0) : item.count;
        const match = count > 0 && terms.every(t => item.search.includes(t));
        item.row.hidden = !match;
        if (match) { proofs++; gaps += count; }
        item.row.querySelector('.gap-count').textContent = `${count} / ${item.count}`;
        item.row.querySelector('.gap-review').href = group ? group.reader_link : item.first;
      }
      document.getElementById('gap-result-count').textContent = `${gaps} explanation gaps in ${proofs} of ${rows.length} readings with gaps`;
      document.getElementById('gap-empty').hidden = proofs !== 0;
      if (persist) {
        const next = new URLSearchParams();
        if (gapSearch.value) next.set('q', gapSearch.value);
        if (gapHead.value) next.set('head', gapHead.value);
        try { history.replaceState(null, '', location.pathname + (next.size ? '?' + next : '') + location.hash); } catch (_) {}
      }
    };
    gapSearch.addEventListener('input', () => apply());
    gapHead.addEventListener('change', () => apply());
    document.getElementById('gap-filters').addEventListener('submit', e => { e.preventDefault(); apply(); });
    window.addEventListener('popstate', () => { restore(); apply(false); });
    restore(); apply(false);
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
