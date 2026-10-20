'use strict';
(() => {
  const data = JSON.parse(document.getElementById('proof-data').textContent);
  const dialog = document.getElementById('source-dialog');
  let previousFocus = null;
  function inspect(element) {
    const row = data.record[element.dataset.kind][Number(element.dataset.index)];
    previousFocus = element;
    document.getElementById('selected-passage').textContent = row.text;
    document.getElementById('selected-record').textContent = JSON.stringify(row, null, 2);
    dialog.showModal();
    document.getElementById('close-dialog').focus();
  }
  document.querySelectorAll('.source-passage').forEach(element => {
    element.addEventListener('click', () => inspect(element));
    element.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        inspect(element);
      }
    });
  });
  document.getElementById('close-dialog').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { if (previousFocus) previousFocus.focus(); });
  const d = data.record.document;
  document.getElementById('composition-record').textContent = JSON.stringify({
    text_theorem: d.text_theorem, bytes_theorem: d.bytes_theorem,
    conclusion_theorem: d.conclusion_theorem,
    closed_outer_binders: d.closed_outer_binders,
    case_split: data.record.skeleton,
    zero_context: data.record.zero_context,
    nonzero_context: data.record.nonzero_context
  }, null, 2);
  function download(name, bytes, type) {
    const url = URL.createObjectURL(new Blob([bytes], {type}));
    const link = document.createElement('a');
    link.href = url; link.download = name;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  document.getElementById('download-proof').addEventListener('click', () =>
    download('bezout-proof.txt', new Uint8Array(d.utf8), 'text/plain;charset=utf-8'));
  document.getElementById('download-record').addEventListener('click', () =>
    download('bezout-document-certificate.json', JSON.stringify({record:data.record, observation:data.observation}, null, 2) + '\n', 'application/json'));
  document.getElementById('download-source').addEventListener('click', () =>
    download('BezoutFrame.lean', data.source, 'text/plain;charset=utf-8'));
  document.getElementById('print').addEventListener('click', () => window.print());
})();
