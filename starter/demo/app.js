const byId = (id) => document.getElementById(id);
let traces = [];
let activeStrategy = 'A';

function plain(value) { return value || 'Không có'; }
function currentTrace() { return traces.find(t => t.question_id === byId('questionSelect').value && t.strategy === activeStrategy); }

function render() {
  const trace = currentTrace();
  if (!trace) return;
  const hits = trace.hits || [];
  byId('questionText').textContent = trace.question;
  byId('splitBadge').textContent = `Split: ${trace.split}`;
  byId('goldPage').textContent = `Gold page: ${trace.gold_page}`;
  byId('expectedAnswer').textContent = trace.expected_answer || 'Xem questions.json';
  byId('goldEvidence').textContent = trace.gold_evidence || 'Xem questions.json';
  byId('metricBadges').innerHTML = [
    `<span class="badge ${trace.hit_at_1 ? '' : 'bad'}">Hit@1: ${trace.hit_at_1 ? 'Có' : 'Không'}</span>`,
    `<span class="badge ${trace.evidence_hit_at_3 ? '' : 'bad'}">Evidence Hit@3: ${trace.evidence_hit_at_3 ? 'Có' : 'Không'}</span>`,
    `<span class="badge neutral">${activeStrategy === 'A' ? 'Fixed-size' : activeStrategy === 'B' ? 'Paragraph' : 'Paragraph + filter'}</span>`
  ].join('');
  byId('hits').innerHTML = hits.map((hit, index) => {
    const m = hit.metadata || {};
    return `<article class="hit">
      <div class="hit-head"><div><p class="rank">TOP ${index + 1}</p><p class="chunk-id">${plain(hit.chunk_id)}</p></div><span class="score">score ${Number(hit.score).toFixed(3)}</span></div>
      <p class="hit-text">${plain(hit.text)}</p>
      <div class="metadata"><span>page ${plain(m.page)}</span><span>${plain(m.chapter)}</span><span>${plain(m.document_type)}</span><span>${hit.evidence_hit ? 'evidence match' : 'no evidence match'}</span></div>
    </article>`;
  }).join('');
}

async function load() {
  try {
    const [traceResponse, questionResponse] = await Promise.all([fetch('../results/traces.json'), fetch('../data/questions.json')]);
    traces = await traceResponse.json();
    const questions = await questionResponse.json();
    const select = byId('questionSelect');
    select.innerHTML = questions.map(q => `<option value="${q.id}">${q.id.toUpperCase()} · ${q.question}</option>`).join('');
    const questionById = Object.fromEntries(questions.map(q => [q.id, q]));
    traces.forEach(t => { t.expected_answer = questionById[t.question_id]?.expected_answer; t.gold_evidence = questionById[t.question_id]?.evidence_quote; });
    select.addEventListener('change', render);
    byId('strategyButtons').addEventListener('click', (event) => {
      const button = event.target.closest('button[data-strategy]');
      if (!button) return;
      activeStrategy = button.dataset.strategy;
      document.querySelectorAll('[data-strategy]').forEach(item => item.classList.toggle('active', item === button));
      render();
    });
    render();
  } catch (error) {
    byId('status').textContent = 'Không thể tải kết quả. Hãy chạy web server từ thư mục starter theo README.';
    console.error(error);
  }
}
load();
