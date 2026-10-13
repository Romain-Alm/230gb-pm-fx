/* Prediction markets and currency strategies: page behaviour.
   Every chart reads window.DATA (assembled by src/report/build_site.py); nothing is typed here.
   Charts are drawn with Plotly (basic bundle, inlined); tables, heatmaps and stat cards are plain DOM. */
(function () {
'use strict';
var D = window.DATA;
var $ = function (id) { return document.getElementById(id); };
var FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
var CONFIG = { responsive: true, displayModeBar: false, scrollZoom: false };
var T = {};

function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function readTheme() {
  T = { ink: cssVar('--ink'), ink2: cssVar('--ink-2'), muted: cssVar('--muted'), grid: cssVar('--grid'), axis: cssVar('--axis'),
        surface: cssVar('--surface'), surface2: cssVar('--surface-2'), wash: cssVar('--wash'), neutral: cssVar('--neutral-series'),
        pos: cssVar('--div-pos'), neg: cssVar('--div-neg'), mid: cssVar('--div-mid'), onLight: cssVar('--on-light') || '#0b0b0b',
        dark: cssVar('--mode') === 'dark', s: [], seq: {} };
  for (var i = 1; i <= 8; i++) T.s.push(cssVar('--s' + i));
  [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700].forEach(function (k) { T.seq[k] = cssVar('--seq-' + k); });
}
var SEQ_STEPS = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700];

/* ------------------------------------------------------------------ formatting */
function f2(v) { return v == null || isNaN(v) ? '' : Number(v).toFixed(2); }
function f1(v) { return v == null || isNaN(v) ? '' : Number(v).toFixed(1); }
function pct(v, d) { return v == null || isNaN(v) ? '' : (100 * v).toFixed(d == null ? 1 : d) + '%'; }
function spct(v, d) { if (v == null || isNaN(v)) return ''; var s = (100 * v).toFixed(d == null ? 1 : d); return (v > 0 ? '+' : '') + s + '%'; }
function fint(v) { return v == null ? '' : Math.round(v).toLocaleString('en-US'); }
function sign2(v) { if (v == null || isNaN(v)) return ''; return (v > 0 ? '+' : '') + Number(v).toFixed(2); }
function hexa(hex, a) {
  var h = hex.replace('#', ''); if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
  var n = parseInt(h, 16); return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + a + ')';
}
function seqColor(share, max) {
  /* one blue ramp, light to dark for magnitude; in dark mode the anchor flips so that small values sit near the surface */
  if (share == null || share <= 0) return null;
  var k = Math.min(SEQ_STEPS.length - 1, Math.floor((share / (max || 1)) * (SEQ_STEPS.length - 1) + 0.5));
  var step = T.dark ? SEQ_STEPS[SEQ_STEPS.length - 1 - k] : SEQ_STEPS[k];
  return { bg: T.seq[step], dark: step >= 450 };
}
function cellText(col) { return col && col.dark ? '#ffffff' : T.onLight; }
function divColor(v, scale) {
  if (v == null || isNaN(v) || v === 0) return { bg: 'transparent', dark: false };
  var a = Math.min(1, Math.abs(v) / scale);
  return { bg: hexa(v > 0 ? T.pos : T.neg, 0.12 + 0.6 * a), dark: a > 0.7 };
}

/* ------------------------------------------------------------------ DOM helpers */
function el(tag, attrs, children) {
  var e = document.createElement(tag);
  if (attrs) Object.keys(attrs).forEach(function (k) {
    if (k === 'text') e.textContent = attrs[k];
    else if (k === 'class') e.className = attrs[k];
    else if (k === 'style') e.setAttribute('style', attrs[k]);
    else if (k.indexOf('on') === 0) e.addEventListener(k.slice(2), attrs[k]);
    else if (attrs[k] != null) e.setAttribute(k, attrs[k]);
  });
  (children || []).forEach(function (c) { if (c != null) e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
  return e;
}
function badge(status) {
  var cls = { 'pre-registered': 'badge-pre', 'a posteriori': 'badge-post', 'exploratory': 'badge-exp', 'benchmark': 'badge-bench' }[status] || 'badge-bench';
  return el('span', { class: 'badge ' + cls, text: status });
}
function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }
/* cells: string | number | {text, cls, title, node, html(false)} */
function buildTable(tbl, head, rows, opts) {
  opts = opts || {};
  clear(tbl);
  var thead = el('thead'), tr = el('tr');
  head.forEach(function (h, i) { tr.appendChild(el('th', { text: typeof h === 'string' ? h : h.text, class: h && h.cls ? h.cls : (i === 0 && opts.rowhead ? 'rowhead' : null) })); });
  thead.appendChild(tr); tbl.appendChild(thead);
  var tbody = el('tbody');
  rows.forEach(function (r) {
    var cells = r.cells || r, trr = el('tr', { class: (r.cls || '') + (r.onclick ? ' clickable' : '') || null, title: r.title || null });
    if (r.onclick) trr.addEventListener('click', r.onclick);
    cells.forEach(function (c, i) {
      var td = el(i === 0 && opts.rowhead ? 'th' : 'td');
      if (c != null && typeof c === 'object' && !(c instanceof Node)) {
        if (c.node) td.appendChild(c.node); else td.textContent = c.text == null ? '' : c.text;
        if (c.cls) td.className = c.cls;
        if (c.title) td.title = c.title;
        if (c.bg) td.style.background = c.bg;
        if (c.color) td.style.color = c.color;
        if (c.data) Object.keys(c.data).forEach(function (k) { td.setAttribute('data-' + k, c.data[k]); });
      } else if (c instanceof Node) td.appendChild(c);
      else td.textContent = c == null ? '' : c;
      if (i === 0 && opts.rowhead) td.className = 'rowhead';
      trr.appendChild(td);
    });
    tbody.appendChild(trr);
  });
  tbl.appendChild(tbody);
}
/* long tables show their first rows and unfold on demand */
function foldTable(tbl, n, what) {
  var wrap = tbl.parentNode, old = wrap.parentNode.querySelector('.fold-btn[data-for="' + tbl.id + '"]');
  if (old) old.remove();
  var rows = tbl.querySelectorAll('tbody tr');
  if (rows.length <= n) return;
  var open = false;
  function apply() { rows.forEach(function (r, i) { r.hidden = !open && i >= n; }); btn.textContent = open ? 'Show the first ' + n + ' only' : 'Show all ' + rows.length + ' ' + what; }
  var btn = el('button', { class: 'chip fold-btn', type: 'button', 'data-for': tbl.id });
  btn.addEventListener('click', function () { open = !open; apply(); if (!open) wrap.scrollIntoView({ block: 'nearest' }); });
  wrap.insertAdjacentElement('afterend', btn);
  apply();
}
function seg(id, onChange) {
  var box = $(id); if (!box) return;
  var btns = box.querySelectorAll('button');
  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      btns.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      onChange(b.getAttribute('data-v'));
    });
  });
}
function segValue(id) { var b = $(id) && $(id).querySelector('button[aria-pressed="true"]'); return b ? b.getAttribute('data-v') : null; }
function fillSelect(sel, options, value) {
  clear(sel);
  options.forEach(function (o) { sel.appendChild(el('option', { value: o.value, text: o.label })); });
  if (value != null) sel.value = value;
}

/* ------------------------------------------------------------------ Plotly helpers */
function isNarrow() { return window.innerWidth < 700; }
function baseLayout(over) {
  var lay = {
    font: { family: FONT, size: 12.5, color: T.ink2 },
    paper_bgcolor: T.surface, plot_bgcolor: T.surface,
    margin: { l: 52, r: 18, t: 10, b: 42 },
    hovermode: 'x unified', dragmode: isNarrow() ? false : 'zoom',
    hoverlabel: { bgcolor: T.surface, bordercolor: T.axis, font: { family: FONT, color: T.ink, size: 12 } },
    xaxis: { gridcolor: T.grid, zeroline: false, linecolor: T.axis, tickcolor: T.axis, tickfont: { color: T.muted }, automargin: true },
    yaxis: { gridcolor: T.grid, zerolinecolor: T.axis, zerolinewidth: 1, showline: false, tickfont: { color: T.muted }, automargin: true },
    showlegend: false,
    legend: { orientation: 'h', x: 0, y: 1.08, xanchor: 'left', yanchor: 'bottom', font: { color: T.ink2, size: 12 }, itemclick: false, itemdoubleclick: false, bgcolor: 'rgba(0,0,0,0)' }
  };
  return merge(lay, over || {});
}
function merge(a, b) {
  Object.keys(b).forEach(function (k) {
    if (b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && a[k] && typeof a[k] === 'object' && !Array.isArray(a[k])) merge(a[k], b[k]);
    else a[k] = b[k];
  });
  return a;
}
var charts = {};
function plot(id, traces, lay) {
  var node = $(id); if (!node) return;
  Plotly.react(node, traces, baseLayout(lay), CONFIG);
}
var MOTION = !(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) && 'IntersectionObserver' in window;
var revealIO = MOTION ? new IntersectionObserver(function (entries) {
  entries.forEach(function (en) {
    if (!en.isIntersecting) return;
    var node = en.target; revealIO.unobserve(node);
    node.classList.remove('pending'); node.classList.add('reveal');
    setTimeout(function () { node.classList.remove('reveal'); }, 1600);
  });
}, { threshold: 0.15 }) : null;
function register(id, fn) { charts[id] = { fn: fn, done: false, node: $(id) }; }
function draw(id) {
  var c = charts[id]; if (!c) return;
  c.fn(); c.done = true;
  if (revealIO && c.node) { c.node.classList.add('pending'); revealIO.observe(c.node); }
}
/* stat values count up from zero the first time they are seen (the final text is always the formatted value) */
var countIO = MOTION ? new IntersectionObserver(function (entries) {
  entries.forEach(function (en) { if (en.isIntersecting) { countIO.unobserve(en.target); countUp(en.target); } });
}, { threshold: 0.5 }) : null;
function countUp(el) {
  var txt = el.textContent, m = /^([-+]?)([\d,]*\.?\d+)([^\d]*)$/.exec(txt);
  if (!m) return;
  var num = parseFloat(m[2].replace(/,/g, '')), dec = (m[2].split('.')[1] || '').length, comma = m[2].indexOf(',') >= 0, t0 = null, dur = 900;
  function fmt(v) { var s = comma ? v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) : v.toFixed(dec); return m[1] + s + m[3]; }
  function step(now) {
    if (t0 == null) t0 = now;
    var p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    el.textContent = p < 1 ? fmt(num * e) : txt;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
function observeCounts(root) { if (countIO) (root || document).querySelectorAll('.stat-value').forEach(function (e) { countIO.observe(e); }); }
function setupReveal() {
  if (!MOTION) return;
  var sel = '.hero > :not(.grid), .sec > :not(.grid):not(.two-col):not(.steps), .grid > *, .two-col > *, .steps > .step';
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
  }, { threshold: 0.06, rootMargin: '0px 0px -30px 0px' });
  document.querySelectorAll(sel).forEach(function (e) {
    var i = Array.prototype.indexOf.call(e.parentNode.children, e);
    e.setAttribute('data-r', '');
    e.style.transitionDelay = (Math.min(i, 5) * 70) + 'ms';
    io.observe(e);
  });
}
function redraw(id) { var c = charts[id]; if (c && c.done) c.fn(); }
function shadeOOS(extra) {
  var sh = [{ type: 'rect', xref: 'x', yref: 'paper', x0: D.meta.oos_start, x1: D.meta.sample_end, y0: 0, y1: 1, fillcolor: T.wash, line: { width: 0 }, layer: 'below' }];
  return sh.concat(extra || []);
}
function oosAnnotation() {
  return { xref: 'x', yref: 'paper', x: D.meta.oos_start, y: 0.98, text: 'out-of-sample', showarrow: false, xanchor: 'left', yanchor: 'top', font: { size: 11, color: T.muted } };
}
function rangeSlider() { return { visible: true, thickness: 0.07, bgcolor: T.surface2, bordercolor: T.axis, borderwidth: 1 }; }
function linkRange(mainId, ddId) {
  var m = $(mainId), d = $(ddId);
  if (!m || !d || m.__linked || !m.on) return;
  m.__linked = true;
  m.on('plotly_relayout', function (ev) {
    if (!d.data) return;
    if (ev['xaxis.autorange']) Plotly.relayout(d, { 'xaxis.autorange': true });
    else if (ev['xaxis.range']) Plotly.relayout(d, { 'xaxis.range': ev['xaxis.range'] });
    else if (ev['xaxis.range[0]'] != null) Plotly.relayout(d, { 'xaxis.range': [ev['xaxis.range[0]'], ev['xaxis.range[1]']] });
  });
}
function drawdownOf(cum) {
  var out = [], peak = -Infinity;
  for (var i = 0; i < cum.length; i++) {
    var w = cum[i] == null ? null : 1 + cum[i] / 100;
    if (w == null) { out.push(null); continue; }
    if (w > peak) peak = w;
    out.push(100 * (w / peak - 1));
  }
  return out;
}
function annotationTrace(dates, series, color) {
  var idx = {}; dates.forEach(function (d, i) { idx[d] = i; });
  var x = [], y = [], txt = [];
  D.annotations.forEach(function (a) {
    var i = idx[a.date]; if (i == null) { for (var j = 0; j < dates.length; j++) if (dates[j] >= a.date) { i = j; break; } }
    if (i == null || series[i] == null) return;
    x.push(dates[i]); y.push(series[i]); txt.push(a.label + ' (' + a.date + ')');
  });
  return { type: 'scatter', mode: 'markers', x: x, y: y, text: txt, hoverinfo: 'text', name: 'event', showlegend: false,
           marker: { size: 9, color: T.surface, line: { color: color || T.ink, width: 2 } } };
}

/* ------------------------------------------------------------------ labels and colours */
var LABEL = {
  A1_theory_with_dollar: 'A1 (primary)', A2_theory_with_dollar: 'A2', 'A1+S_theory_with_dollar': 'A1 + geopolitics',
  A2_theory_dollar_neutral: 'A2 dollar-neutral', A1_theory_with_dollar_weekly: 'A1 weekly', 'A1_theory_with_dollar_cost0.5x': 'A1, costs 0.5x',
  'A2_theory_with_dollar_cost0.5x': 'A2, costs 0.5x', A1_gated20_frozen: '20-day rule (D30)',
  base_carry: 'EM carry, base', pm_timed: 'PM-timed carry', vix_timed: 'VIX-timed carry', pm_timed_without_event: 'PM-timed without Taiwan',
  b2_oil_tilt: 'B2, oil tilt', b2_brent_tilt: 'B2, Brent trigger', pm_timed_min3events: '3-events overlay (D31)'
};
function label(id) { return LABEL[id] || id; }
var DESC = {
  A1_theory_with_dollar: 'The primary rule: the US monetary and US fiscal-political cells (USD 50k, 60% gate), with theory-given signs. The forecast is common to the nine pairs, so it is a long or short dollar position against an inverse-variance G10 basket.',
  A2_theory_with_dollar: 'Every G10-zone cell of the monetary, inflation and fiscal-political themes at the USD 10k threshold, without the gate, each active when it has contracts. The forecast then differs across pairs.',
  'A1+S_theory_with_dollar': 'A1 plus the contracts of Strategy B\'s index as spillovers: global geopolitics on JPY and CHF, the oil composite on NOK and CAD, China tariffs on AUD and NZD.',
  A2_theory_dollar_neutral: 'A2 with the common dollar component of the weights removed each day: only the cross-country differences are traded.',
  A1_theory_with_dollar_weekly: 'A1 rebalanced on the last trading day of each week instead of daily.',
  'A1_theory_with_dollar_cost0.5x': 'The positions of A1 charged half the Bloomberg composite half-spread (a cost scenario, not a different rule).',
  'A2_theory_with_dollar_cost0.5x': 'The positions of A2 charged half the Bloomberg composite half-spread.',
  A1_gated20_frozen: 'The spec\'s gated rule at a 20-day horizon: components with the right sign and t above 3 on 2024-2025, frozen coefficients, rebalanced every 20 trading days. The horizon was chosen after seeing the data.',
  base_carry: 'Each month, rank six floating EM currencies on their one-month forward premium; long the top two, short the bottom two, inverse-volatility weights, 10% volatility target.',
  pm_timed: 'The base carry scaled by the exposure of the prediction-market overlay: the month-end escalation weight and the cuts on confirmed geopolitical shocks.',
  vix_timed: 'The same overlay driven by VIX instead of the geopolitics index: the ex ante benchmark.',
  pm_timed_without_event: 'The overlay rebuilt with the geopolitics index computed without the single contract behind the June 2024 cut.',
  b2_oil_tilt: 'A confirmed shock carried mostly by oil-related contracts does not cut the carry: it tilts the book towards oil exporters and away from importers, sized by the avoided cut.',
  b2_brent_tilt: 'The same tilt, triggered by a daily Brent rise of more than two standard deviations instead of the prediction-market index.',
  pm_timed_min3events: 'The overlay recomputed on days with at least three distinct events behind the index, so that one contract cannot drive a cut.'
};
function glossary(tblId, items) {
  var t = $(tblId); if (!t) return;
  buildTable(t, ['Line', 'What it is', 'Status'], items.map(function (it) { return [{ text: it.label, cls: 'txt' }, { text: DESC[it.id] || '', cls: 'txt' }, { node: badge(it.status) }]; }));
}
var STATUS = D.labels.status;
function statusOf(id) { return STATUS[id] || 'pre-registered'; }
function colorA(id) {
  return { A1_theory_with_dollar: T.s[0], A2_theory_with_dollar: T.s[1], 'A1+S_theory_with_dollar': T.s[2], A2_theory_dollar_neutral: T.s[3],
           A1_theory_with_dollar_weekly: T.s[4], 'A1_theory_with_dollar_cost0.5x': T.s[5], 'A2_theory_with_dollar_cost0.5x': T.s[6], A1_gated20_frozen: T.s[7] }[id] || T.neutral;
}
function colorB(id) {
  return { base_carry: T.neutral, pm_timed: T.s[0], vix_timed: T.s[7], pm_timed_without_event: T.s[0], b2_oil_tilt: T.s[1], pm_timed_min3events: T.s[2] }[id] || T.neutral;
}
function colorRisk(id) {
  return { A1_theory_with_dollar: T.s[0], A2_theory_with_dollar: T.s[1], 'A1+S_theory_with_dollar': T.s[2], base_carry: T.neutral, pm_timed: T.s[3], vix_timed: T.s[7] }[id] || T.neutral;
}
var PERIOD = D.labels.period;
function perf(key, strategy, period) {
  var rows = D[key].performance;
  for (var i = 0; i < rows.length; i++) if (rows[i].strategy === strategy && rows[i].period === period) return rows[i];
  return null;
}

/* ------------------------------------------------------------------ state */
var state = { gross: false, aSel: ['A1_theory_with_dollar', 'A2_theory_with_dollar'], aAnn: true, aStat: 'A1_theory_with_dollar', aPeriod: 'full',
              bSel: ['base_carry', 'pm_timed', 'vix_timed', 'pm_timed_without_event'], bAnn: true, bStat: 'base_carry', bPeriod: 'full', taiwan: false,
              hl: D.meta.halflife, sigCell: D.signals.order[0], sigWeight: 'index_vw', sigAnn: true,
              covPeriod: 'share_train', covSet: 'cells', gate: Math.round(100 * D.coverage.gate), expoVix: false,
              placeboA: 'A1', d30: 'sharpe_2026', gridCut: D.robustness.grid_b_chosen.shock_cut, llStudy: D.timing.leadlag.studies[0], episode: null, cursor: null, gridPick: null };
function episodeShapes() {
  var e = state.episode; if (!e) return [];
  return [{ type: 'rect', xref: 'x', yref: 'paper', x0: e.start, x1: e.end, y0: 0, y1: 1, fillcolor: hexa(T.s[6], 0.16), line: { width: 0 }, layer: 'below' }];
}
function episodeAnnotation() {
  var e = state.episode; if (!e) return [];
  return [{ xref: 'x', yref: 'paper', x: e.start, y: 0.03, text: e.name, showarrow: false, xanchor: 'left', yanchor: 'bottom', font: { size: 11, color: T.ink2 } }];
}

/* ================================================================== 2. data */
function hazard() {
  var p = Number($('hz-p').value) / 100, tau = Number($('hz-tau').value);
  var lam = -Math.log(1 - p) / tau;
  $('hz-p-out').textContent = Math.round(100 * p) + '%';
  $('hz-tau-out').textContent = tau + ' days';
  $('hz-out').textContent = (100 * lam).toFixed(2) + '%';
  var x = [], y = [];
  for (var t = 0; t <= tau; t++) { x.push(t); y.push(100 * (1 - Math.exp(-lam * (tau - t)))); }
  plot('fig-hazard', [{ type: 'scatter', mode: 'lines', x: x, y: y, line: { color: T.s[0], width: 2 }, name: 'raw probability (%)', hovertemplate: 'day %{x}: %{y:.1f}%<extra></extra>' }],
       { xaxis: { title: { text: 'days elapsed (deadline at ' + tau + ')', font: { size: 12 } } }, yaxis: { title: { text: 'probability (%)', font: { size: 12 } }, range: [0, 100] },
         annotations: [{ xref: 'paper', yref: 'paper', x: 0.98, y: 0.95, xanchor: 'right', text: 'constant hazard ' + (100 * lam).toFixed(2) + '% a day', showarrow: false, font: { size: 12, color: T.ink2 } }] });
}
function hazardReal() {
  var h = D.walk.hazard_example, win = D.walk.contract_rows;
  var traces = [
    { type: 'scatter', mode: 'lines', x: h.dates, y: h.px.map(function (v) { return v == null ? null : 100 * v; }), customdata: h.ttr_days, name: 'traded probability (%)',
      line: { color: T.neutral, width: 2 }, hovertemplate: '%{y:.0f}%, %{customdata:.0f} days to the deadline<extra>probability</extra>' },
    { type: 'scatter', mode: 'lines', x: h.dates, y: h.hazard, name: 'implied hazard rate (per year)', yaxis: 'y2', line: { color: T.s[0], width: 2 }, hovertemplate: '%{y:.2f} a year<extra>hazard rate</extra>' }
  ];
  var x0 = win[0].day, x1 = win[win.length - 1].day;
  plot('fig-hazard-real', traces, {
    showlegend: true,
    yaxis: { domain: [0.56, 1], title: { text: 'probability (%)', font: { size: 12 } }, rangemode: 'tozero' },
    yaxis2: { domain: [0, 0.44], title: { text: 'hazard rate (per year)', font: { size: 12 } }, gridcolor: T.grid, tickfont: { color: T.muted }, rangemode: 'tozero' },
    shapes: [{ type: 'rect', xref: 'x', yref: 'paper', x0: x0, x1: x1, y0: 0, y1: 1, fillcolor: hexa(T.s[1], 0.14), line: { width: 0 }, layer: 'below' },
             { type: 'line', xref: 'x', yref: 'paper', x0: D.walk.contract.deadline, x1: D.walk.contract.deadline, y0: 0, y1: 1, line: { color: T.axis, width: 1 } }],
    annotations: [{ xref: 'x', yref: 'paper', x: x0, y: 0.98, text: 'worked example', showarrow: false, xanchor: 'left', yanchor: 'top', font: { size: 11, color: T.muted } },
                  { xref: 'x', yref: 'paper', x: D.walk.contract.deadline, y: 0.5, text: 'deadline', showarrow: false, xanchor: 'right', font: { size: 11, color: T.muted }, textangle: -90 }]
  });
}
function walkTables() {
  var W = D.walk, rows = W.contract_rows, peak = rows.reduce(function (a, b) { return Math.abs(b.z) > Math.abs(a.z) ? b : a; }, rows[0]);
  buildTable($('tbl-walk-contract'), ['Day', 'p', 'Days to deadline', 'Hazard (a year)', 'Change', 'Own vol', 'z (signed)', 'Weight in cell', 'Contribution', 'Contracts in cell', 'Cell change', 'Index'],
    rows.map(function (r) {
      return { cells: [r.day, Math.round(100 * r.px) + 'c', f1(r.ttr_days), f2(r.hazard_per_year), sign2(r.dv), f2(r.sd), sign2(r.z), pct(r.weight_share, 0), sign2(r.contribution), fint(r.n_contracts), sign2(r.d_vw), f1(r.index_vw)],
               cls: r === peak ? 'hl primary' : null, title: r.gap_days > 1 ? 'change spans ' + r.gap_days + ' days, divided by its square root' : null };
    }), { rowhead: true });
  foldTable($('tbl-walk-contract'), 6, 'days');
  var A = W.cell_a, flip = A.filter(function (r) { return r.usd_position > 0; })[0];
  buildTable($('tbl-walk-a'), ['Day', 'US monetary change', 'Smoothed s', 'Z MON', 'Z FIS', 'Regime R', 'Forecast y', 'USD position (x capital)', 'Gross'],
    A.map(function (r) {
      return { cells: [r.day, sign2(r.d_mon), sign2(r.s_mon), sign2(r.Z_mon), sign2(r.Z_fis), r.R, sign2(r.y), { text: sign2(r.usd_position), cls: r.usd_position > 0 ? 'pos' : 'neg' }, f2(r.gross)],
               cls: r === flip ? 'hl primary' : null };
    }), { rowhead: true });
  foldTable($('tbl-walk-a'), 7, 'days');
  buildTable($('tbl-walk-geo'), ['Day', 'Cell change', 'Contracts', 'Index', 'Escalation', 'z', 'Raw shock', 'Confirmed', 'Month-end weight', 'Shock cut', 'Exposure w'],
    W.geo.map(function (r) {
      var closed = r.w == null;
      return { cells: [r.day, sign2(r.d), fint(r.n_contracts), f1(r.index), f2(r.escalation), r.escalation_z == null ? '' : f2(r.escalation_z), r.shock_raw ? 'yes' : '', r.confirmed ? 'yes' : '',
                       closed ? { text: 'closed', cls: 'muted' } : f2(r.w_escalation), closed ? '' : (r.shock ? 'cut' : ''), closed ? '' : { text: f2(r.w), cls: r.w < 1 ? 'neg' : '' }],
               cls: r.confirmed ? 'hl primary' : null };
    }), { rowhead: true });
  foldTable($('tbl-walk-geo'), 10, 'days');
}
function classChart() {
  var rows = D.classification.by_theme, themes = rows.map(function (r) { return r.theme; });
  var traces = ['kalshi', 'polymarket'].map(function (pf, i) {
    var sub = {}; D.classification.summary.forEach(function (r) { if (r.platform === pf) sub[r.theme] = r; });
    return { type: 'bar', orientation: 'h', name: pf === 'kalshi' ? 'Kalshi' : 'Polymarket', y: themes.map(function (t) { return D.labels.theme[t] || t; }),
             x: themes.map(function (t) { return sub[t] ? sub[t].markets : 0; }),
             customdata: themes.map(function (t) { return sub[t] ? [sub[t].usable, sub[t].markets ? sub[t].usable / sub[t].markets : 0, sub[t].events] : [0, 0, 0]; }),
             marker: { color: T.s[i] }, hovertemplate: '%{x:,} markets, %{customdata[2]:,} events, %{customdata[1]:.0%} usable<extra>' + (pf === 'kalshi' ? 'Kalshi' : 'Polymarket') + '</extra>' };
  });
  plot('fig-class', traces, { barmode: 'stack', bargap: 0.35, showlegend: true, legend: { traceorder: 'normal' }, hovermode: 'y unified', margin: { l: 110 }, xaxis: { title: { text: 'markets with trades', font: { size: 12 } }, tickformat: ',' }, yaxis: { autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } });
}
function examples() {
  var box = $('ex-filters'), tbl = $('tbl-examples');
  var fTheme = 'all', fPlat = 'all';
  var themes = Object.keys(D.labels.theme).filter(function (t) { return D.classification.examples.some(function (e) { return e.theme === t; }); });
  function render() {
    var rows = D.classification.examples.filter(function (e) { return (fTheme === 'all' || e.theme === fTheme) && (fPlat === 'all' || e.platform === fPlat); });
    buildTable(tbl, ['Platform', 'Contract', 'Theme', 'Zone', 'Direction', 'Rule'], rows.map(function (e) {
      var dir = e.partition ? 'bucket' : (e.direction > 0 ? '+1' : e.direction < 0 ? '−1' : '0');
      return [e.platform, { text: e.title, cls: 'txt' }, D.labels.theme[e.theme] || e.theme, e.zones || 'none', dir, { text: e.theme_rule + ' / ' + e.direction_rule, cls: 'txt' }];
    }));
    foldTable(tbl, 8, 'contracts');
  }
  function chips(items, cur, set) {
    var wrap = el('span', { class: 'chips' });
    items.forEach(function (it) {
      var b = el('button', { class: 'chip', type: 'button', 'aria-pressed': it.value === cur ? 'true' : 'false', text: it.label });
      b.addEventListener('click', function () { set(it.value); build(); });
      wrap.appendChild(b);
    });
    return wrap;
  }
  function build() {
    clear(box);
    box.appendChild(el('label', { text: 'Theme' }));
    box.appendChild(chips([{ value: 'all', label: 'all' }].concat(themes.map(function (t) { return { value: t, label: D.labels.theme[t] || t }; })), fTheme, function (v) { fTheme = v; }));
    box.appendChild(el('label', { text: 'Platform' }));
    box.appendChild(chips([{ value: 'all', label: 'all' }, { value: 'kalshi', label: 'Kalshi' }, { value: 'polymarket', label: 'Polymarket' }], fPlat, function (v) { fPlat = v; }));
    render();
  }
  build();
}

/* ================================================================== 3. coverage */
function coverage() {
  var cells = D.coverage[state.covSet], field = state.covPeriod, gate = state.gate / 100;
  var map = {}; cells.forEach(function (c) { map[c.zone + '/' + c.theme] = c; });
  var nPass = cells.filter(function (c) { return c[field] >= gate && c[field] > 0; }).length;
  $('gate-out').textContent = state.gate + '%';
  $('gate-count').textContent = nPass + ' cell' + (nPass === 1 ? '' : 's') + ' pass' + (nPass === 1 ? 'es' : '') + ' the gate';
  var head = [{ text: 'Zone' }].concat(D.coverage.themes.map(function (t) { return D.labels.theme[t]; }));
  var rows = D.coverage.zones.map(function (z) {
    return [z].concat(D.coverage.themes.map(function (t) {
      var c = map[z + '/' + t], v = c ? c[field] : 0;
      if (!c || v <= 0) return { text: '', cls: 'cell' };
      var col = seqColor(Math.sqrt(v), 1), pass = v >= gate;   /* square-root scale: small shares stay distinguishable */
      return { text: Math.round(100 * v) + '%', cls: 'cell' + (pass ? ' pass' : ' fail'), bg: col.bg, color: cellText(col),
               title: z + ' / ' + D.labels.theme[t] + ': ' + pct(v) + ' of weekdays, ' + fint(c.n_contracts) + ' contracts, ' + fint(c.n_events) + ' events, USD ' + f1(c.volume_usd_m) + 'm' };
    }));
  });
  buildTable($('tbl-coverage'), head, rows, { rowhead: true });
}
function coverageFull() {
  var rows = D.coverage.cells.slice().sort(function (a, b) { return b.share_train - a.share_train; });
  buildTable($('tbl-coverage-full'), ['Zone', 'Theme', '2024-2025', '2026', 'Contracts', 'Events', 'Volume (USD m)', 'Kept'],
    rows.map(function (c) { return { cells: [c.zone, D.labels.theme[c.theme] || c.theme, pct(c.share_train), pct(c.share_test), fint(c.n_contracts), fint(c.n_events), f1(c.volume_usd_m), { node: el('span', { class: 'badge ' + (c.keep ? 'badge-kept' : 'badge-out'), text: c.keep ? 'kept' : 'out' }) }], cls: c.keep ? 'primary' : null }; }));
  foldTable($('tbl-coverage-full'), 10, 'cells');
}

/* ================================================================== 4. signals */
function signals() {
  var cell = D.signals.cells[state.sigCell], dates = D.signals.dates, y = cell[state.sigWeight];
  var traces = [
    { type: 'scatter', mode: 'lines', x: dates, y: y, name: cell.label, line: { color: cell.kept ? T.s[0] : T.neutral, width: 2 }, connectgaps: false, hovertemplate: '%{y:.2f} sd<extra>' + cell.label + '</extra>' },
    { type: 'bar', x: dates, y: cell.n_contracts, name: 'contracts behind the index', yaxis: 'y2', marker: { color: T.seq[250] }, hovertemplate: '%{y} contracts<extra></extra>' }
  ];
  if (state.sigAnn) traces.push(annotationTrace(dates, y, T.ink));
  plot('fig-signals', traces, {
    showlegend: true, hovermode: 'x unified', bargap: 0,
    yaxis: { domain: [0.3, 1], title: { text: 'index (sd)', font: { size: 12 } } },
    yaxis2: { domain: [0, 0.22], title: { text: 'contracts', font: { size: 12 } }, gridcolor: T.grid, tickfont: { color: T.muted }, rangemode: 'tozero' },
    xaxis: { range: [D.meta.sample_start, D.meta.sample_end], rangeslider: rangeSlider() },
    shapes: shadeOOS(), annotations: [oosAnnotation()]
  });
}

/* ================================================================== 5. timing */
function horizon() {
  var rows = D.timing.tstats, get = function (model, reg, h) { for (var i = 0; i < rows.length; i++) if (rows[i].model === model && rows[i].regressor === reg && rows[i].horizon === h) return rows[i]; return null; };
  var spec = [[0, 'Same day', 'A1_contemporaneous'], [1, '1 day ahead', 'A1_predictive'], [5, '5 days ahead', 'A1_predictive'], [20, '20 days ahead', 'A1_predictive']];
  var body = spec.map(function (s) {
    return [{ text: s[1] }].concat(['MONETARY', 'FISCAL_POLITICAL'].map(function (reg) {
      var r = get(s[2], reg, s[0]); if (!r) return { text: '' };
      var col = divColor(r.t, 4), c = { text: f2(r.t), cls: 'cell' + (Math.abs(r.t) > 2 ? ' pass' : ''), bg: col.bg, color: col.dark ? '#fff' : T.ink,
        title: 'coefficient ' + r.coef.toFixed(5) + ', s.e. ' + r.se.toFixed(5) + ', p = ' + r.p.toFixed(3) + ', ' + fint(r.n_obs) + ' pair-days' };
      if (reg === 'FISCAL_POLITICAL' && s[0] === 20) {
        c.node = el('a', { href: '#not-a-result', style: 'color:inherit;text-decoration:none' }, [f2(r.t), el('span', { class: 'badge badge-exp', text: 'exploratory' })]);
      }
      return c;
    }));
  });
  buildTable($('tbl-horizon'), ['Horizon', 'US monetary', 'US fiscal'], body, { rowhead: true });
}
function leadlag() {
  var rows = D.timing.leadlag.rows.filter(function (r) { return r.study === state.llStudy; }).sort(function (a, b) { return a.hour - b.hour; });
  var fx = state.llStudy.indexOf('PM ') === 0, k = fx ? 1e4 : 1, unit = fx ? 'bp' : 'sd';
  var x = rows.map(function (r) { return r.hour; });
  var traces = [
    { type: 'scatter', x: x, y: rows.map(function (r) { return k * r.ci_high; }), mode: 'lines', line: { width: 0 }, hoverinfo: 'skip', showlegend: false },
    { type: 'scatter', x: x, y: rows.map(function (r) { return k * r.ci_low; }), mode: 'lines', line: { width: 0 }, fill: 'tonexty', fillcolor: hexa(T.s[0], 0.12), name: '95% band', hoverinfo: 'skip' },
    { type: 'scatter', x: x, y: rows.map(function (r) { return k * r.mean; }), mode: 'lines+markers', line: { color: T.s[0], width: 2 }, marker: { size: 8, color: T.s[0], line: { color: T.surface, width: 2 } }, name: 'mean response', hovertemplate: 'hour %{x}: %{y:.3f} ' + unit + '<extra></extra>' }
  ];
  plot('fig-leadlag', traces, { showlegend: true, xaxis: { title: { text: 'hours from the event (' + fint(rows[0] ? rows[0].n_events : 0) + ' events)', font: { size: 12 } }, dtick: 1 }, yaxis: { title: { text: (fx ? 'FX dollar-basket return (bp)' : 'PM index change (sd)'), font: { size: 12 } } },
    shapes: [{ type: 'line', xref: 'x', yref: 'paper', x0: 0, x1: 0, y0: 0, y1: 1, line: { color: T.axis, width: 1 } }] });
}
function weekendTable() {
  buildTable($('tbl-weekend'), ['Model', 'Component', 'Coefficient', 't', 'Pair-weekends'], D.timing.weekend.rows.map(function (r) {
    return { cells: [r.model, r.regressor, r.coef.toFixed(4), f2(r.t), fint(r.n_obs)], cls: r.model.indexOf('A1+GEO') === 0 ? 'primary' : null };
  }));
  foldTable($('tbl-weekend'), 8, 'rows');
}

/* ================================================================== 6. strategy A */
function chipsFor(boxId, items, selected, onToggle) {
  var box = clear($(boxId));
  items.forEach(function (it) {
    var on = selected.indexOf(it.id) >= 0;
    var b = el('button', { class: 'chip', type: 'button', 'aria-pressed': on ? 'true' : 'false', title: (DESC[it.id] ? DESC[it.id] + ' ' : '') + '(' + it.status + ')' },
      [el('span', { class: 'key' + (it.dashed ? ' dashed' : ''), style: 'background:' + (it.dashed ? 'none' : it.color) + ';color:' + it.color }), it.label]);
    b.addEventListener('click', function () { onToggle(it.id); });
    box.appendChild(b);
  });
}
function aCum() {
  var dates = D.strategy_a.dates, src = state.gross ? D.strategy_a.cum_gross : D.strategy_a.cum_net;
  var traces = [], dd = [];
  state.aSel.forEach(function (id) {
    var y = src[id]; if (!y) return;
    var v = D.strategy_a.variants.filter(function (x) { return x.id === id; })[0];
    traces.push({ type: 'scatter', mode: 'lines', x: dates, y: y, name: label(id) + (v && v.status !== 'pre-registered' ? ' (' + v.status + ')' : ''), line: { color: colorA(id), width: 2, dash: v && v.status === 'exploratory' ? 'dot' : 'solid' }, hovertemplate: '%{y:.1f}%<extra>' + label(id) + '</extra>' });
    dd.push({ type: 'scatter', mode: 'lines', x: dates, y: drawdownOf(y), name: label(id), line: { color: colorA(id), width: 1.5 }, fill: 'tozeroy', fillcolor: hexa(colorA(id), 0.08), hovertemplate: '%{y:.1f}%<extra>' + label(id) + '</extra>' });
  });
  if (state.aAnn && traces.length) traces.push(annotationTrace(dates, src[state.aSel[0]], T.ink));
  plot('fig-a-cum', traces, { showlegend: true, xaxis: { rangeslider: rangeSlider() }, yaxis: { title: { text: (state.gross ? 'gross' : 'net') + ' cumulative return (%)', font: { size: 12 } }, ticksuffix: '%' }, shapes: shadeOOS(episodeShapes()), annotations: [oosAnnotation()].concat(episodeAnnotation()) });
  plot('fig-a-dd', dd, { margin: { t: 4, b: 30 }, yaxis: { title: { text: 'drawdown (%)', font: { size: 11 } }, ticksuffix: '%' }, shapes: shadeOOS(episodeShapes()) });
  linkRange('fig-a-cum', 'fig-a-dd');
}
function statCards(boxId, r, opts) {
  var box = clear($(boxId)); opts = opts || {};
  function card(labelText, value, sub) { box.appendChild(el('div', { class: 'stat' }, [el('div', { class: 'stat-label', text: labelText }), el('div', { class: 'stat-value', text: value }), sub ? el('div', { class: 'stat-sub', text: sub }) : null])); }
  if (!r) { card('No statistics', 'n/a', opts.note || ''); return; }
  var star = opts.star ? '*' : '';
  card('Sharpe ratio', f2(r.sharpe) + star, (r.sharpe_t != null ? 't = ' + f2(r.sharpe_t) : (opts.note || '')) + (star ? '; * conservative costs' : ''));
  if (r.sharpe_ci90_low != null) card('90% interval', f2(r.sharpe_ci90_low) + ' to ' + f2(r.sharpe_ci90_high), 'block bootstrap');
  card('Annual return', pct(r.ann_mean), r.n_days ? fint(r.n_days) + ' days' : '');
  if (r.ann_vol != null) card('Volatility', pct(r.ann_vol), 'annualised');
  card('Max drawdown', pct(r.max_drawdown), r.max_dd_duration_days ? r.max_dd_duration_days + ' days to recover' : '');
  if (r.hit_rate != null) card('Positive days', pct(r.hit_rate), '');
  if (!opts.gross) {
    if (r.turnover_ann != null) card('Turnover', f1(r.turnover_ann) + 'x', 'of capital a year');
    if (r.cost_drag_ann != null) card('Cost drag', pct(r.cost_drag_ann), 'a year');
  }
  observeCounts(box);
}
function aCards() {
  var id = state.aStat, key = state.gross ? D.strategy_a.gross_of[id] : id;
  var r = perf('strategy_a', key, state.aPeriod);
  statCards('cards-a', r, { gross: state.gross, star: !state.gross && id.indexOf('cost0.5x') < 0 });
  var b = clear($('a-stat-badge')); b.appendChild(badge(statusOf(id))); b.appendChild(document.createTextNode(' ' + (state.gross ? 'gross, before costs' : 'net of costs') + ', ' + PERIOD[state.aPeriod]));
}
function aLadder() {
  var items = [['A1_theory_with_dollar_gross', 'A1 gross'], ['A1_theory_with_dollar', 'A1 net (primary)'], ['A2_theory_with_dollar_gross', 'A2 gross'], ['A2_theory_with_dollar', 'A2 net'],
               ['A2_theory_dollar_neutral', 'A2 dollar-neutral net'], ['A1+S_theory_with_dollar', 'A1 + geopolitics net']];
  var rows = items.map(function (it) { return { r: perf('strategy_a', it[0], 'full'), name: it[1], primary: it[0] === 'A1_theory_with_dollar' }; }).reverse();
  var ylab = rows.map(function (x) { return x.name + ': ' + f2(x.r.sharpe); });
  plot('fig-a-ladder', [{ type: 'bar', orientation: 'h', y: ylab, x: rows.map(function (x) { return x.r.sharpe; }),
    marker: { color: rows.map(function (x) { return x.primary ? T.s[0] : T.seq[250]; }) }, width: 0.55,
    error_x: { type: 'data', symmetric: false, array: rows.map(function (x) { return x.r.sharpe_ci90_high - x.r.sharpe; }), arrayminus: rows.map(function (x) { return x.r.sharpe - x.r.sharpe_ci90_low; }), color: T.ink2, thickness: 1, width: 4 },
    hovertemplate: 'Sharpe %{x:.2f}, 90%% interval %{customdata[0]:.2f} to %{customdata[1]:.2f}<extra></extra>', customdata: rows.map(function (x) { return [x.r.sharpe_ci90_low, x.r.sharpe_ci90_high]; }) }],
    { hovermode: 'y', margin: { l: 10, r: 20 }, xaxis: { zeroline: true, zerolinecolor: T.ink, zerolinewidth: 1.5, title: { text: 'annualised Sharpe ratio, 2024-2026, with 90% intervals', font: { size: 12 } } }, yaxis: { automargin: true, gridcolor: 'rgba(0,0,0,0)', tickfont: { color: T.ink, size: 12 } } });
}
function histChart(id, h, name, extraText) {
  var centers = [], widths = [];
  for (var i = 0; i < h.counts.length; i++) { centers.push((h.edges[i] + h.edges[i + 1]) / 2); widths.push(h.edges[i + 1] - h.edges[i]); }
  var ann = [{ xref: 'x', yref: 'paper', x: h.actual, y: 1, text: 'actual ' + f2(h.actual) + ', beats ' + Math.round(100 * h.share_beaten) + '%', showarrow: true, arrowhead: 0, ax: h.actual > h.mean_draw ? -70 : 70, ay: -4, font: { size: 12, color: T.ink }, arrowcolor: T.ink }];
  if (extraText) ann.push({ xref: 'paper', yref: 'paper', x: 0.02, y: 0.98, xanchor: 'left', yanchor: 'top', text: extraText, showarrow: false, align: 'left', font: { size: 11.5, color: T.ink2 }, bgcolor: hexa(T.surface, 0.8) });
  plot(id, [{ type: 'bar', x: centers, y: h.counts, width: widths, marker: { color: T.seq[300] }, name: name, hovertemplate: 'Sharpe %{x:.2f}: %{y} draws<extra></extra>' }],
    { bargap: 0.08, hovermode: 'x', xaxis: { title: { text: 'annualised Sharpe of ' + h.n + ' date-shuffled draws', font: { size: 12 } } }, yaxis: { title: { text: 'draws', font: { size: 12 } } },
      shapes: [{ type: 'line', xref: 'x', yref: 'paper', x0: h.actual, x1: h.actual, y0: 0, y1: 1, line: { color: T.ink, width: 2 } }], annotations: ann });
}
function aPlacebo() {
  var h = D.strategy_a.robustness.placebo[state.placeboA];
  histChart('fig-a-placebo', h, state.placeboA, 'random contracts: ' + f2(h.random_contracts) + '<br>reversed signs: ' + f2(h.reversed) + '<br>equal weights: ' + f2(h.equal_weights));
}
function halflife() {
  var strip = clear($('a-halflife')), grid = D.meta.halflife_grid;
  grid.forEach(function (hl) {
    var b = el('button', { class: 'chip', type: 'button', 'aria-pressed': hl === state.hl ? 'true' : 'false', text: hl + ' day' + (hl > 1 ? 's' : '') + (hl === D.meta.halflife ? ' (primary)' : '') });
    b.addEventListener('click', function () { state.hl = hl; halflife(); });
    strip.appendChild(b);
  });
  var box = clear($('a-halflife-cards'));
  ['A1', 'A2'].forEach(function (v) {
    var r = D.strategy_a.robustness.halflife.filter(function (x) { return x.variant === v && x.halflife === state.hl; })[0];
    box.appendChild(el('div', { class: 'stat' }, [el('div', { class: 'stat-label', text: v + ', net Sharpe with a ' + state.hl + '-day half-life' }), el('div', { class: 'stat-value', text: r ? f2(r.sharpe) : 'n/a' }), el('div', { class: 'stat-sub', text: r ? 'max drawdown ' + pct(r.max_drawdown) + ', return ' + pct(r.ann_mean) + ' a year' : '' })]));
  });
}
function aLoo() {
  var rows = D.strategy_a.robustness.leave_one_out.filter(function (r) { return r.variant === 'A1'; });
  var actual = D.strategy_a.robustness.placebo.A1.actual;
  plot('fig-a-loo', [{ type: 'scatter', mode: 'markers', y: rows.map(function (r) { return r.event; }), x: rows.map(function (r) { return r.sharpe; }), marker: { size: 10, color: T.s[0], line: { color: T.surface, width: 2 } }, name: 'A1 without the event',
    customdata: rows.map(function (r) { return r.max_drawdown; }), hovertemplate: 'Sharpe %{x:.2f}, max drawdown %{customdata:.1%}<extra>without %{y}</extra>' }],
    { hovermode: 'closest', margin: { l: 10, r: 20 }, xaxis: { title: { text: 'net Sharpe of A1 with the event removed', font: { size: 12 } } }, yaxis: { automargin: true, tickfont: { size: 11 }, gridcolor: 'rgba(0,0,0,0)' },
      shapes: [{ type: 'line', xref: 'x', yref: 'paper', x0: actual, x1: actual, y0: 0, y1: 1, line: { color: T.ink, width: 1.5 } }],
      annotations: [{ xref: 'x', yref: 'paper', x: actual, y: 1.02, text: 'all events: ' + f2(actual), showarrow: false, yanchor: 'bottom', font: { size: 11.5, color: T.ink } }] });
}
function aRobustTable() {
  var R = D.strategy_a.robustness, p = R.placebo, mom = {}, st = {};
  R.momentum_benchmarks.forEach(function (r) { mom[r.series + '|' + r.period] = r; });
  R.static_timing.forEach(function (r) { st[r.strategy + '|' + r.part + '|' + r.period] = r; });
  var loo = R.leave_one_out.filter(function (r) { return r.variant === 'A1'; }).map(function (r) { return r.sharpe; });
  var w = perf('strategy_a', 'A1_theory_with_dollar_weekly', 'full'), c1 = perf('strategy_a', 'A1_theory_with_dollar_cost0.5x', 'full'), c2 = perf('strategy_a', 'A2_theory_with_dollar_cost0.5x', 'full');
  var rows = [
    ['Date-shuffle placebo', 'A1 beats ' + Math.round(100 * p.A1.share_beaten) + '% of draws, A2 ' + Math.round(100 * p.A2.share_beaten) + '%', 'pre-registered'],
    ['Leave one event out', 'A1 Sharpe stays ' + f2(Math.min.apply(null, loo)) + ' to ' + f2(Math.max.apply(null, loo)), 'pre-registered'],
    ['Static vs timing (D25)', 'timing carries the P&L: ' + f2(st['A1_theory_with_dollar|timing|full'].sharpe) + ' vs ' + f2(st['A1_theory_with_dollar|static|full'].sharpe) + ' gross', 'pre-registered'],
    ['Random contracts, reversed signs', 'A1: ' + f2(p.A1.random_contracts) + ' and ' + f2(p.A1.reversed), 'pre-registered'],
    ['Equal weights in the cell index', 'A1 ' + f2(p.A1.equal_weights) + ', A2 ' + f2(p.A2.equal_weights), 'pre-registered'],
    ['Spec rule: |t| > ' + D.meta.gate_abs_t + ' to trade', 'selects nothing; largest t = ' + f2(R.gate.largest_t), 'pre-registered'],
    ['Dollar momentum benchmark', 'gross Sharpe ' + f2(mom['TSMOM 1d|2024-2026'].gross_sharpe) + ' (1 day), ' + f2(mom['TSMOM 5d|2024-2026'].gross_sharpe) + ' (5 days)', 'exploratory'],
    ['Weekly rebalancing', 'net ' + f2(w.sharpe) + ', turnover ' + f1(w.turnover_ann), 'a posteriori'],
    ['Costs at 0.5x', 'A1 ' + f2(c1.sharpe) + ', A2 ' + f2(c2.sharpe), 'a posteriori']
  ];
  buildTable($('tbl-a-robust'), ['Check', 'Result', 'Status'], rows.map(function (r) { return [{ text: r[0], cls: 'txt' }, { text: r[1], cls: 'txt' }, { node: badge(r[2]) }]; }));
}
function momentumTable() {
  var rows = D.strategy_a.robustness.momentum_benchmarks, by = {};
  rows.forEach(function (r) { (by[r.series] = by[r.series] || {})[r.period] = r; });
  buildTable($('tbl-momentum'), ['Series', 'Gross Sharpe 2024-2025', '2026', '2024-2026', 'Net Sharpe 2024-2026'], Object.keys(by).map(function (s) {
    var b = by[s]; return [s, f2(b['2024-2025'].gross_sharpe), f2(b['2026'].gross_sharpe), f2(b['2024-2026'].gross_sharpe), f2(b['2024-2026'].net_sharpe)];
  }));
}
function gateTable() {
  buildTable($('tbl-gate'), ['Variant', 'Component', 'Coefficient (1 day)', 't', 'Pair-days', 'Passes |t| > ' + D.meta.gate_abs_t], D.strategy_a.robustness.gate.rows.map(function (r) {
    return [r.variant, r.regressor, r.coef.toFixed(5), f2(r.t), fint(r.n_obs), r.passes_gate ? 'yes' : 'no'];
  }));
}
function d30() {
  var ph = D.strategy_a.d30.phase, col = state.d30, y = ph.map(function (r) { return r[col]; });
  var mean = y.reduce(function (a, b) { return a + b; }, 0) / y.length;
  plot('fig-d30', [{ type: 'bar', x: ph.map(function (r) { return r.offset; }), y: y, marker: { color: ph.map(function (r) { return r.offset === 0 ? T.s[1] : T.seq[300]; }) }, width: 0.6,
    hovertemplate: 'start offset %{x}: Sharpe %{y:.2f}<extra></extra>', name: 'phase' }],
    { hovermode: 'x', bargap: 0.3, xaxis: { title: { text: 'rebalancing start offset (trading days); 0 = published', font: { size: 12 } }, dtick: 1 }, yaxis: { title: { text: 'net Sharpe', font: { size: 12 } } },
      shapes: [{ type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: mean, y1: mean, line: { color: T.ink, width: 1.5 } }],
      annotations: [{ xref: 'paper', yref: 'y', x: 1, y: mean, text: 'mean ' + f2(mean), showarrow: false, xanchor: 'right', yanchor: 'bottom', font: { size: 12, color: T.ink } }] });
}
function d30Tables() {
  buildTable($('tbl-d30-monthly'), ['Month (2026)', 'Net', 'Gross', 'USD position at month-end'], D.strategy_a.d30.monthly_2026.map(function (r) {
    return [r.month, spct(r.net), spct(r.gross), (r.usd_position_month_end > 0 ? 'long USD (' : 'short USD (') + sign2(r.usd_position_month_end) + ')'];
  }));
  buildTable($('tbl-d30-decomp'), ['Part', 'Period', 'Sharpe', 'Annual return', 'Volatility'], D.strategy_a.d30.decomposition.map(function (r) {
    return [r.part.replace(/_/g, ' '), r.period, f2(r.sharpe), pct(r.ann_mean), pct(r.ann_vol)];
  }));
}

/* ================================================================== 7. strategy B */
function universeChips() {
  var box = clear($('universe-chips'));
  D.strategy_b.universe.filter(function (u) { return u.primary_universe; }).forEach(function (u) {
    box.appendChild(el('span', { class: 'ccy' }, [el('b', { text: u.ccy }), 'IRR ' + (u.irr_fine_code != null ? Math.round(u.irr_fine_code) : '') + ', ' + u.irr_label]));
  });
}
function universeTable() {
  buildTable($('tbl-universe'), ['Currency', 'IRR fine code', 'De facto regime', 'Primary universe', 'Coarse 9-13 variant'], D.strategy_b.universe.map(function (u) {
    return { cells: [u.ccy, u.irr_fine_code != null ? Math.round(u.irr_fine_code) : '', { text: u.irr_label, cls: 'txt' }, u.primary_universe ? 'yes' : 'no', u.coarse12_variant ? 'yes' : 'no'], cls: u.primary_universe ? 'primary' : null };
  }));
  foldTable($('tbl-universe'), 8, 'currencies');
}
function lh() {
  var c = D.strategy_b.long_history.cum;
  plot('fig-lh', [{ type: 'scatter', mode: 'lines', x: c.dates, y: c.values, line: { color: T.neutral, width: 1.5 }, name: 'base carry, net', hovertemplate: '%{y:.0f}%<extra></extra>' }],
    { margin: { l: 44, r: 10, t: 6, b: 30 }, yaxis: { ticksuffix: '%', title: { text: 'cumulative (%)', font: { size: 11 } } }, shapes: [{ type: 'rect', xref: 'x', yref: 'paper', x0: D.meta.sample_start, x1: D.meta.sample_end, y0: 0, y1: 1, fillcolor: T.wash, line: { width: 0 }, layer: 'below' }],
      annotations: [{ xref: 'x', yref: 'paper', x: D.meta.sample_start, y: 0.96, text: 'our window', showarrow: false, xanchor: 'right', font: { size: 10.5, color: T.muted } }] });
}
function geo() {
  var g = D.strategy_b.geo, idx = {}; g.dates.forEach(function (d, i) { idx[d] = i; });
  var sh = g.confirmed_shocks;
  var traces = [
    { type: 'scatter', mode: 'lines', x: g.dates, y: g.index, name: 'global geopolitics index', line: { color: T.s[0], width: 2 }, connectgaps: false, hovertemplate: '%{y:.1f} sd<extra>index</extra>' },
    { type: 'scatter', mode: 'markers', x: sh.map(function (s) { return s.day; }), y: sh.map(function (s) { var i = idx[s.day]; return i == null ? null : g.index[i]; }), name: 'confirmed shock',
      marker: { size: sh.map(function (s) { return 8 + 2.2 * Math.sqrt(s.n_contracts); }), color: T.s[1], line: { color: T.surface, width: 2 } },
      customdata: sh.map(function (s) { return [s.n_contracts, s.d, s.volume_usd]; }), hovertemplate: '%{customdata[0]} contracts, move %{customdata[1]:.2f} sd, USD %{customdata[2]:,.0f}<extra>shock %{x}</extra>' },
    { type: 'bar', x: g.dates, y: g.n_contracts, name: 'contracts behind the index', yaxis: 'y2', marker: { color: T.seq[250] }, hovertemplate: '%{y} contracts<extra></extra>' }
  ];
  plot('fig-geo', traces, { showlegend: true, bargap: 0, yaxis: { domain: [0.3, 1], title: { text: 'index (sd)', font: { size: 12 } } }, yaxis2: { domain: [0, 0.22], gridcolor: T.grid, tickfont: { color: T.muted }, title: { text: 'contracts', font: { size: 12 } }, rangemode: 'tozero' },
    shapes: shadeOOS([{ type: 'rect', xref: 'x', yref: 'paper', x0: D.strategy_b.key_month.month + '-01', x1: nextMonth(D.strategy_b.key_month.month), y0: 0, y1: 1, fillcolor: hexa(T.s[1], 0.10), line: { width: 0 }, layer: 'below' }]),
    annotations: [oosAnnotation(), { xref: 'x', yref: 'paper', x: D.strategy_b.key_month.month + '-01', y: 0.98, text: 'June 2024 cut', showarrow: false, xanchor: 'left', yanchor: 'top', font: { size: 11, color: T.muted } }] });
}
function nextMonth(ym) { var y = Number(ym.slice(0, 4)), m = Number(ym.slice(5, 7)); m += 1; if (m > 12) { m = 1; y += 1; } return y + '-' + (m < 10 ? '0' : '') + m + '-01'; }
function expo() {
  var dates = D.strategy_b.dates, e = D.strategy_b.exposure;
  var shockX = [], shockY = []; e.shock.forEach(function (s, i) { if (s) { shockX.push(dates[i]); shockY.push(e.w[i]); } });
  var traces = [
    { type: 'scatter', mode: 'lines', x: dates, y: e.w_escalation, name: 'monthly escalation component', line: { color: T.seq[250], width: 2, shape: 'hv' }, hovertemplate: '%{y:.2f}<extra>escalation component</extra>' },
    { type: 'scatter', mode: 'lines', x: dates, y: e.w, name: 'exposure w(t), PM overlay', line: { color: T.s[0], width: 2, shape: 'hv' }, hovertemplate: '%{y:.2f}<extra>exposure</extra>' },
    { type: 'scatter', mode: 'markers', x: shockX, y: shockY, name: 'confirmed shock', marker: { size: 8, color: T.s[1], line: { color: T.surface, width: 2 } }, hovertemplate: 'shock<extra>%{x}</extra>' }
  ];
  if (state.expoVix) traces.push({ type: 'scatter', mode: 'lines', x: dates, y: e.w_vix, name: 'exposure, VIX overlay', line: { color: T.s[7], width: 1.5, shape: 'hv' }, hovertemplate: '%{y:.2f}<extra>VIX overlay</extra>' });
  plot('fig-expo', traces, { showlegend: true, yaxis: { range: [0, 1.06], title: { text: 'share of the carry position', font: { size: 12 } } }, shapes: expoShapes(), annotations: [oosAnnotation()] });
}
var bExtra = [];
function cursorShape() { return state.cursor ? [{ type: 'line', xref: 'x', yref: 'paper', x0: state.cursor, x1: state.cursor, y0: 0, y1: 1, line: { color: T.ink, width: 1.5 } }] : []; }
function bShapes() { return shadeOOS(bExtra).concat(cursorShape()); }
function expoShapes() { return shadeOOS().concat(cursorShape()); }
/* replay: a cursor sweeps the exposure and the cumulative chart of B, with a live readout */
var play = { timer: null, i: 0 };
function stopPlay(clearCursor) {
  if (play.timer) cancelAnimationFrame(play.timer);
  play.timer = null;
  var b = $('expo-play'); if (b) b.textContent = 'Replay the overlay day by day';
  if (clearCursor) { state.cursor = null; redraw('fig-expo'); redraw('fig-b-cum'); if ($('expo-readout')) $('expo-readout').textContent = ''; }
}
function togglePlay() {
  if (play.timer) { stopPlay(false); return; }
  ['fig-expo', 'fig-b-cum'].forEach(function (id) { if (charts[id] && !charts[id].done) draw(id); });
  var dates = D.strategy_b.dates, e = D.strategy_b.exposure, cb = D.strategy_b.cum_net, out = $('expo-readout'), expoNode = $('fig-expo'), cumNode = $('fig-b-cum');
  var step = Math.max(1, Math.round(dates.length / 360));
  play.i = 0; $('expo-play').textContent = 'Stop';
  function frame() {
    play.i += step;
    if (play.i >= dates.length) { stopPlay(true); return; }
    state.cursor = dates[play.i];
    Plotly.relayout(expoNode, { shapes: expoShapes() });
    Plotly.relayout(cumNode, { shapes: bShapes() });
    out.textContent = dates[play.i] + ': exposure ' + f2(e.w[play.i]) + (e.shock[play.i] ? ' (shock)' : '') + ', net cumulative: base carry ' + f1(cb.base_carry[play.i]) + '%, PM-timed ' + f1(cb.pm_timed[play.i]) + '%';
    play.timer = requestAnimationFrame(frame);
  }
  play.timer = requestAnimationFrame(frame);
}
function bCum() {
  var dates = D.strategy_b.dates, src = state.gross ? D.strategy_b.cum_gross : D.strategy_b.cum_net;
  var traces = [], dd = [];
  state.bSel.forEach(function (id) {
    var y = src[id]; if (!y) return;
    var st = statusOf(id), dashed = id === 'pm_timed_without_event';
    traces.push({ type: 'scatter', mode: 'lines', x: dates, y: y, name: label(id) + (st !== 'pre-registered' ? ' (' + st + ')' : ''), line: { color: colorB(id), width: 2, dash: dashed ? 'dash' : 'solid' }, hovertemplate: '%{y:.1f}%<extra>' + label(id) + '</extra>' });
    dd.push({ type: 'scatter', mode: 'lines', x: dates, y: drawdownOf(y), name: label(id), line: { color: colorB(id), width: 1.5, dash: dashed ? 'dash' : 'solid' }, hovertemplate: '%{y:.1f}%<extra>' + label(id) + '</extra>' });
  });
  var km = D.strategy_b.key_month.month;
  var extra = [{ type: 'rect', xref: 'x', yref: 'paper', x0: km + '-01', x1: nextMonth(km), y0: 0, y1: 1, fillcolor: hexa(T.s[1], 0.10), line: { width: 0 }, layer: 'below' }].concat(episodeShapes());
  if (state.bAnn && traces.length) traces.push(annotationTrace(dates, src[state.bSel[0]], T.ink));
  bExtra = extra;
  plot('fig-b-cum', traces, { showlegend: true, xaxis: { rangeslider: rangeSlider() }, yaxis: { title: { text: (state.gross ? 'gross' : 'net') + ' cumulative return (%)', font: { size: 12 } }, ticksuffix: '%' }, shapes: bShapes(), annotations: [oosAnnotation(), { xref: 'x', yref: 'paper', x: km + '-01', y: 0.98, text: 'June 2024', showarrow: false, xanchor: 'left', yanchor: 'top', font: { size: 11, color: T.muted } }].concat(episodeAnnotation()) });
  plot('fig-b-dd', dd, { margin: { t: 4, b: 30 }, yaxis: { title: { text: 'drawdown (%)', font: { size: 11 } }, ticksuffix: '%' }, shapes: shadeOOS(extra) });
  linkRange('fig-b-cum', 'fig-b-dd');
}
function bCards() {
  var b = clear($('b-stat-badge'));
  if (state.taiwan) {
    var row = D.strategy_b.key_month.rows.filter(function (r) { return r.strategy === 'pm_timed_without_event'; })[0];
    statCards('cards-b', { sharpe: row.sharpe, ann_mean: row.ann_mean, max_drawdown: row.max_drawdown }, { note: 'full sample, net' });
    b.appendChild(badge('a posteriori')); b.appendChild(document.createTextNode(' PM overlay rebuilt without "' + D.strategy_b.key_month.event + '", 2024-2026, net of costs (D29)'));
    return;
  }
  var id = state.bStat, key = state.gross ? id + '_gross' : id, r = perf('strategy_b', key, state.bPeriod);
  if (!r && state.gross) { r = perf('strategy_b', id, state.bPeriod); statCards('cards-b', r, { gross: true }); b.appendChild(badge(statusOf(id))); b.appendChild(document.createTextNode(' no gross series for this line, net shown, ' + PERIOD[state.bPeriod])); return; }
  statCards('cards-b', r, { gross: state.gross });
  b.appendChild(badge(statusOf(id))); b.appendChild(document.createTextNode(' ' + (state.gross ? 'gross, before costs' : 'net of costs') + ', ' + PERIOD[state.bPeriod]));
}
function keyMonth() {
  var k = D.strategy_b.key_month, names = [k.month + ' alone', 'all other months', 'total'], vals = [100 * k.gain, 100 * k.others, 100 * k.total];
  plot('fig-b-keymonth', [{ type: 'bar', x: names, y: vals, marker: { color: vals.map(function (v) { return v >= 0 ? T.pos : T.neg; }) }, width: 0.5, text: vals.map(function (v) { return (v > 0 ? '+' : '') + v.toFixed(1); }), textposition: 'outside', textfont: { color: T.ink, size: 12 }, cliponaxis: false, hovertemplate: '%{y:.1f} points<extra>%{x}</extra>', name: 'gap' }],
    { hovermode: 'x', xaxis: { gridcolor: 'rgba(0,0,0,0)' }, yaxis: { title: { text: 'PM-timed minus base carry (points)', font: { size: 12 } }, zeroline: true, zerolinecolor: T.ink } });
}
function bLadder() {
  var items = [['pm_timed', 'PM-timed overlay'], ['base_carry', 'EM carry, base (primary)'], ['pm_timed_without_event', 'without the Taiwan contract (a posteriori)'], ['vix_timed', 'VIX-timed (benchmark)'], ['b2_oil_tilt', 'B2, oil tilt (a posteriori)'], ['pm_timed_min3events', '3-events overlay (a posteriori)']];
  var rows = items.map(function (it) {
    var r = perf('strategy_b', it[0], 'full');
    if (!r && it[0] === 'pm_timed_without_event') { var w = D.strategy_b.key_month.rows.filter(function (x) { return x.strategy === it[0]; })[0]; r = { sharpe: w.sharpe, sharpe_ci90_low: null, sharpe_ci90_high: null }; }
    return { r: r, name: it[1], primary: it[0] === 'base_carry' };
  }).reverse();
  var ylab = rows.map(function (x) { return x.name + ': ' + f2(x.r.sharpe); });
  plot('fig-b-ladder', [{ type: 'bar', orientation: 'h', y: ylab, x: rows.map(function (x) { return x.r.sharpe; }), width: 0.55,
    marker: { color: rows.map(function (x) { return x.primary ? T.s[0] : T.seq[250]; }) },
    error_x: { type: 'data', symmetric: false, array: rows.map(function (x) { return x.r.sharpe_ci90_high == null ? 0 : x.r.sharpe_ci90_high - x.r.sharpe; }), arrayminus: rows.map(function (x) { return x.r.sharpe_ci90_low == null ? 0 : x.r.sharpe - x.r.sharpe_ci90_low; }), color: T.ink2, thickness: 1, width: 4 },
    hovertemplate: 'Sharpe %{x:.2f}<extra></extra>' }],
    { hovermode: 'y', margin: { l: 10, r: 20 }, xaxis: { zeroline: true, zerolinecolor: T.ink, zerolinewidth: 1.5, title: { text: 'net Sharpe, 2024-2026, with 90% intervals where available', font: { size: 12 } } }, yaxis: { automargin: true, gridcolor: 'rgba(0,0,0,0)', tickfont: { color: T.ink, size: 11.5 } } });
}
function composition() {
  var c = D.strategy_b.composition, x = c.map(function (r) { return r.currency; });
  var w = c.map(function (r) { return 100 * r.average_weight; }), b = c.map(function (r) { return r.brent_beta_weekly; });
  plot('fig-b-comp', [
    { type: 'bar', x: x, y: w, name: 'average position (% of capital)', marker: { color: w.map(function (v) { return v >= 0 ? T.pos : T.neg; }) }, width: 0.5, text: w.map(function (v) { return (v > 0 ? '+' : '') + v.toFixed(0) + '%'; }), textposition: 'outside', textfont: { color: T.ink, size: 12 }, cliponaxis: false, hovertemplate: '%{y:.0f}% of capital<extra>%{x}</extra>' },
    { type: 'bar', x: x, y: b, name: 'weekly beta to Brent', xaxis: 'x2', yaxis: 'y2', marker: { color: b.map(function (v) { return v >= 0 ? T.pos : T.neg; }) }, width: 0.5, text: b.map(function (v) { return sign2(v); }), textposition: 'outside', textfont: { color: T.ink, size: 11 }, cliponaxis: false, hovertemplate: 'Brent beta %{y:.3f}<extra>%{x}</extra>' }
  ], { grid: { rows: 1, columns: 2, pattern: 'independent' }, hovermode: 'closest', showlegend: false, margin: { t: 28 },
       xaxis: { gridcolor: 'rgba(0,0,0,0)', domain: [0, 0.46] }, yaxis: { title: { text: 'average position, % of capital', font: { size: 12 } }, zeroline: true, zerolinecolor: T.ink },
       xaxis2: { gridcolor: 'rgba(0,0,0,0)', domain: [0.56, 1] }, yaxis2: { title: { text: 'weekly beta to Brent', font: { size: 12 } }, zeroline: true, zerolinecolor: T.ink, gridcolor: T.grid, tickfont: { color: T.muted } },
       annotations: [{ xref: 'paper', yref: 'paper', x: 0, y: 1.06, text: 'Average position, 2024-2026', showarrow: false, xanchor: 'left', font: { size: 12.5, color: T.ink } }, { xref: 'paper', yref: 'paper', x: 0.56, y: 1.06, text: 'Weekly beta of the currency to Brent', showarrow: false, xanchor: 'left', font: { size: 12.5, color: T.ink } }] });
}

/* ================================================================== 8. risk */
var RISK_SHOW = ['A1_theory_with_dollar', 'A2_theory_with_dollar', 'base_carry', 'pm_timed', 'vix_timed'];
function episodes() {
  var eps = [], seen = {};
  D.risk.episodes.forEach(function (r) { if (!seen[r.episode]) { seen[r.episode] = true; eps.push(r); } });
  eps.sort(function (a, b) { return a.start < b.start ? -1 : 1; });
  var by = {}; D.risk.episodes.forEach(function (r) { by[r.episode + '|' + r.strategy] = r; });
  buildTable($('tbl-episodes'), [{ text: 'Episode' }].concat(RISK_SHOW.map(label)), eps.map(function (e) {
    var on = state.episode && state.episode.name === e.episode;
    var cells = [{ node: el('span', {}, [el('b', { text: e.episode }), el('br'), el('span', { class: 'small', style: 'color:var(--muted)', text: e.start + ' to ' + e.end + ', ' + e.n_days + ' days' })]), cls: 'txt' }].concat(RISK_SHOW.map(function (s) {
      var r = by[e.episode + '|' + s]; if (!r) return { text: '' };
      var col = divColor(r.cum_return, 0.08);
      return { text: spct(r.cum_return), cls: 'cell', bg: col.bg, color: col.dark ? '#fff' : T.ink, title: 'worst day ' + spct(r.worst_day) };
    }));
    return { cells: cells, cls: on ? 'hl' : null, title: on ? 'click to remove the highlight' : 'click to shade this window on the cumulative charts of sections 6 and 7',
             onclick: function () { state.episode = on ? null : { name: e.episode, start: e.start, end: e.end }; episodes(); redraw('fig-a-cum'); redraw('fig-b-cum'); } };
  }), { rowhead: true });
}
var FACTOR_LABEL = { spx: 'S&P 500', msci_world: 'MSCI World', brent: 'Brent', dollar: 'Dollar', g10_carry: 'G10 carry', em_carry: 'EM carry', d_vix: 'VIX change' };
function betas() {
  var sid = $('beta-strategy').value, rows = D.risk.betas.filter(function (r) { return r.strategy === sid; });
  var order = Object.keys(FACTOR_LABEL).filter(function (f) { return rows.some(function (r) { return r.factor === f; }); });
  var by = {}; rows.forEach(function (r) { by[r.factor] = r; });
  var t = order.map(function (f) { return by[f].t; });
  plot('fig-betas', [{ type: 'bar', x: order.map(function (f) { return FACTOR_LABEL[f]; }), y: t, width: 0.5, marker: { color: t.map(function (v) { return v >= 0 ? T.pos : T.neg; }) },
    text: t.map(function (v) { return Math.abs(v) > 2 ? f1(v) : ''; }), textposition: 'outside', textfont: { color: T.ink, size: 12 }, cliponaxis: false,
    customdata: order.map(function (f) { return [by[f].beta, by[f].corr]; }), hovertemplate: 't = %{y:.2f}, beta %{customdata[0]:.3f}, correlation %{customdata[1]:.2f}<extra>%{x}</extra>', name: label(sid) }],
    { hovermode: 'x', xaxis: { gridcolor: 'rgba(0,0,0,0)' }, yaxis: { title: { text: 't-statistic of the weekly beta', font: { size: 12 } }, zeroline: true, zerolinecolor: T.ink },
      shapes: [2, -2].map(function (v) { return { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: v, y1: v, line: { color: T.axis, width: 1 } }; }) });
}
function downside() {
  var mk = $('down-market').value, rows = D.risk.downside.filter(function (r) { return r.market === mk && RISK_SHOW.indexOf(r.strategy) >= 0; });
  rows.sort(function (a, b) { return RISK_SHOW.indexOf(a.strategy) - RISK_SHOW.indexOf(b.strategy); });
  var y = rows.map(function (r) { return label(r.strategy); });
  var traces = rows.map(function (r, i) { return { type: 'scatter', mode: 'lines', x: [r.beta, r.downside_beta], y: [y[i], y[i]], line: { color: T.axis, width: 2 }, hoverinfo: 'skip', showlegend: false }; });
  traces.push({ type: 'scatter', mode: 'markers', x: rows.map(function (r) { return r.beta; }), y: y, name: 'beta, all weeks', marker: { size: 10, color: T.neutral, line: { color: T.surface, width: 2 } }, hovertemplate: 'beta %{x:.2f}<extra>%{y}</extra>' });
  traces.push({ type: 'scatter', mode: 'markers', x: rows.map(function (r) { return r.downside_beta; }), y: y, name: 'downside beta', marker: { size: 10, color: T.s[0], line: { color: T.surface, width: 2 } }, customdata: rows.map(function (r) { return [r.n_down, r.mean_return_down_days_bp]; }), hovertemplate: 'downside beta %{x:.2f} (%{customdata[0]} weeks, mean %{customdata[1]:.0f} bp)<extra>%{y}</extra>' });
  plot('fig-downside', traces, { showlegend: true, hovermode: 'closest', margin: { l: 10 }, xaxis: { zeroline: true, zerolinecolor: T.ink, title: { text: 'weekly beta to ' + (mk === 'msci_world' ? 'MSCI World' : 'the EM carry factor'), font: { size: 12 } } }, yaxis: { automargin: true, autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } });
}
var BUCKET = { 'VIX tercile': { q1: 'low VIX', q2: 'middle', q3: 'high VIX' }, 'half-spread tercile': { q1: 'low spreads (most liquid)', q2: 'middle', q3: 'high spreads (least liquid)' },
               'dollar month': { '1.0': 'dollar up', '-1.0': 'dollar down', '1': 'dollar up', '-1': 'dollar down' }, 'geo shock day': { 'True': 'shock day', 'False': 'other days' }, 'large Brent week': { 'True': 'large Brent move', 'False': 'other weeks' } };
function conditional() {
  var cond = $('cond-select').value, rows = D.risk.conditional.filter(function (r) { return r.conditioner === cond; });
  var buckets = []; rows.forEach(function (r) { var b = String(r.bucket); if (buckets.indexOf(b) < 0) buckets.push(b); });
  var by = {}; rows.forEach(function (r) { by[String(r.bucket) + '|' + r.strategy] = r; });
  buildTable($('tbl-conditional'), [{ text: 'State' }].concat(RISK_SHOW.map(label)), buckets.map(function (b) {
    return [(BUCKET[cond] && BUCKET[cond][b]) || b].concat(RISK_SHOW.map(function (s) {
      var r = by[b + '|' + s]; if (!r) return { text: '' };
      var col = divColor(r.sharpe, 3);
      return { text: f2(r.sharpe), cls: 'cell', bg: col.bg, color: col.dark ? '#fff' : T.ink, title: 'annual return ' + pct(r.ann_mean) + ', ' + fint(r.n_days) + ' days' };
    }));
  }), { rowhead: true });
}
function worstDD() {
  var sid = $('dd-strategy').value, rows = D.risk.worst_drawdowns.filter(function (r) { return r.strategy === sid; });
  buildTable($('tbl-worst-dd'), ['Peak', 'Trough', 'Recovery', 'Depth', 'Duration (days)', 'News between peak and trough'], rows.map(function (r) {
    return [r.peak, r.trough, r.recovery || 'ongoing', pct(r.depth), fint(r.duration_days), { text: r.tag, cls: 'txt' }];
  }));
}
function concentration() {
  var groups = {}; D.risk.concentration.forEach(function (r) { var k = r.strategy + '|' + r.dimension; (groups[k] = groups[k] || { strategy: r.strategy, dimension: r.dimension, hhi: r.hhi, items: [] }).items.push(r); });
  buildTable($('tbl-concentration'), ['Strategy', 'Dimension', 'HHI', 'Largest contributor'], Object.keys(groups).map(function (k) {
    var g = groups[k]; g.items.sort(function (a, b) { return b.share_of_abs - a.share_of_abs; });
    return [label(g.strategy), g.dimension, f2(g.hhi), g.items[0].key + ' (' + pct(g.items[0].share_of_abs, 0) + ' of absolute P&L)'];
  }));
}
function leverage() {
  buildTable($('tbl-leverage'), ['Strategy', 'Period', 'Mean gross', '95th pct', 'Max', 'Realised vol', 'Gross cap binds', 'Pair cap binds'], D.risk.leverage.map(function (r) {
    return [label(r.strategy), r.period, f2(r.gross_mean), f2(r.gross_p95), f2(r.gross_max), pct(r.realised_vol), r.cap_days_measured ? pct(r.share_days_gross_cap) : 'no cap', r.cap_days_measured ? pct(r.share_days_pair_cap) : 'no cap'];
  }));
  foldTable($('tbl-leverage'), 6, 'rows');
}

/* ================================================================== 9. robustness */
function placeboAll() {
  var v = $('placebo-select').value, h, extra;
  if (v === 'B') { h = D.robustness.placebo_b; extra = 'base carry: ' + f2(h.base_carry) + '<br>random contracts: ' + f2(h.random_contracts) + '<br>reversed signs: ' + f2(h.reversed); }
  else if (D.strategy_a.robustness.placebo[v]) { h = D.strategy_a.robustness.placebo[v]; extra = 'random contracts: ' + f2(h.random_contracts) + '<br>reversed signs: ' + f2(h.reversed); }
  else { h = D.robustness.posthoc[v]; extra = 'random contracts: ' + f2(h.random_contracts) + '<br>reversed signs: ' + f2(h.reversed); }
  histChart('fig-placebo', h, v, extra);
}
function grid() {
  var G = D.robustness.grid_b, ch = D.robustness.grid_b_chosen, cut = Number(state.gridCut);
  var ks = [], rs = []; G.forEach(function (r) { if (ks.indexOf(r.shock_k) < 0) ks.push(r.shock_k); if (rs.indexOf(r.rerisk_days) < 0) rs.push(r.rerisk_days); });
  ks.sort(function (a, b) { return a - b; }); rs.sort(function (a, b) { return a - b; });
  var by = {}; G.forEach(function (r) { by[r.shock_k + '|' + r.rerisk_days + '|' + r.shock_cut] = r; });
  var max = Math.max.apply(null, G.map(function (r) { return r.sharpe; }));
  buildTable($('tbl-grid'), [{ text: 'Shock threshold' }].concat(rs.map(function (r) { return 're-risk ' + r + ' d'; })), ks.map(function (k) {
    return [k.toFixed(1) + ' sd'].concat(rs.map(function (r) {
      var c = by[k + '|' + r + '|' + cut]; if (!c) return { text: '' };
      var col = seqColor(c.sharpe, max), chosen = k === ch.shock_k && r === ch.rerisk_days && cut === ch.shock_cut;
      var picked = state.gridPick && state.gridPick.k === k && state.gridPick.r === r && state.gridPick.cut === cut;
      return { text: f2(c.sharpe), cls: 'cell pick' + (chosen ? ' chosen pass' : '') + (picked ? ' picked' : ''), bg: col ? col.bg : 'transparent', color: col ? cellText(col) : T.ink,
               title: 'max drawdown ' + pct(c.max_drawdown) + ', annual return ' + pct(c.ann_mean), data: { k: k, r: r } };
    }));
  }), { rowhead: true });
}
function gridPick(td) {
  var k = Number(td.getAttribute('data-k')), r = Number(td.getAttribute('data-r')), cut = Number(state.gridCut);
  var c = D.robustness.grid_b.filter(function (x) { return x.shock_k === k && x.rerisk_days === r && x.shock_cut === cut; })[0];
  if (!c) return;
  state.gridPick = { k: k, r: r, cut: cut };
  var ch = D.robustness.grid_b_chosen, isChosen = k === ch.shock_k && r === ch.rerisk_days && cut === ch.shock_cut;
  $('grid-pick').textContent = 'Shock threshold ' + k.toFixed(1) + ' sd, re-risk over ' + r + ' days, cut to ' + Math.round(100 * cut) + '%' + (isChosen ? ' (the chosen rule)' : '') + ': net Sharpe ' + f2(c.sharpe) + ', max drawdown ' + pct(c.max_drawdown) + ', annual return ' + pct(c.ann_mean) + '.';
  grid();
}
function cost() {
  var cb = D.robustness.cost_b, ca = D.robustness.cost_a, mults = cb.map(function (r) { return r.cost_multiplier; });
  var xs = mults.map(function (m) { return m + 'x'; });
  function pick(v) { return mults.map(function (m) { var r = ca.filter(function (x) { return x.variant === v && x.multiplier === m; })[0]; return r ? r.sharpe : null; }); }
  plot('fig-cost', [
    { type: 'bar', x: xs, y: cb.map(function (r) { return r.sharpe; }), name: 'PM-timed carry', marker: { color: T.s[0] }, text: cb.map(function (r) { return f2(r.sharpe); }), textposition: 'outside', textfont: { color: T.ink, size: 11 }, cliponaxis: false, hovertemplate: 'Sharpe %{y:.2f}<extra>PM-timed carry, %{x} costs</extra>' },
    { type: 'bar', x: xs, y: pick('A1'), name: 'A1', marker: { color: T.s[1] }, text: pick('A1').map(function (v) { return v == null ? '' : f2(v); }), textposition: 'outside', textfont: { color: T.ink, size: 11 }, cliponaxis: false, hovertemplate: 'Sharpe %{y:.2f}<extra>A1, %{x} costs</extra>' },
    { type: 'bar', x: xs, y: pick('A2'), name: 'A2', marker: { color: T.s[2] }, text: pick('A2').map(function (v) { return v == null ? '' : f2(v); }), textposition: 'outside', textfont: { color: T.ink, size: 11 }, cliponaxis: false, hovertemplate: 'Sharpe %{y:.2f}<extra>A2, %{x} costs</extra>' }
  ], { barmode: 'group', bargap: 0.3, bargroupgap: 0.08, showlegend: true, hovermode: 'x', xaxis: { title: { text: 'cost multiple (1x = half the forward bid-ask)', font: { size: 12 } }, gridcolor: 'rgba(0,0,0,0)' }, yaxis: { title: { text: 'net Sharpe, 2024-2026', font: { size: 12 } }, zeroline: true, zerolinecolor: T.ink } });
}
function subperiods() {
  var by = {}, order = []; D.robustness.subperiods.forEach(function (r) { if (!by[r.strategy]) { by[r.strategy] = {}; order.push(r.strategy); } by[r.strategy][r.period] = r; });
  var years = ['2024', '2025', '2026'];
  buildTable($('tbl-subperiods'), ['Strategy', 'Status'].concat(years), order.map(function (s) {
    return { cells: [label(s), { node: badge(statusOf(s)) }].concat(years.map(function (y) { var r = by[s][y]; if (!r) return ''; var col = divColor(r.sharpe, 3); return { text: f2(r.sharpe), bg: col.bg, color: col.dark ? '#fff' : T.ink, title: 'return ' + pct(r.ann_mean) + ', max drawdown ' + pct(r.max_drawdown) }; })), cls: s === 'A1_theory_with_dollar' || s === 'base_carry' ? 'primary' : null };
  }));
}
function robustOther() {
  var pa = D.strategy_a.robustness.placebo, pb = D.robustness.placebo_b, post = D.robustness.posthoc;
  var loo = pb.leave_one_out.map(function (r) { return r.sharpe; });
  var vt = {}; pb.volume_threshold.forEach(function (r) { vt[r.threshold] = r.sharpe; });
  var rows = [
    ['Actual rule', f2(pa.A1.actual), f2(pa.A2.actual), f2(pb.actual)],
    ['Equal weights in the index', f2(pa.A1.equal_weights), f2(pa.A2.equal_weights), f2(pb.equal_weights)],
    ['Random contracts (placebo b)', f2(pa.A1.random_contracts), f2(pa.A2.random_contracts), f2(pb.random_contracts)],
    ['Reversed signs (placebo c)', f2(pa.A1.reversed), f2(pa.A2.reversed), f2(pb.reversed)],
    ['Volume threshold USD 10k / 250k', '', '', f2(vt['10k']) + ' / ' + f2(vt['250k'])],
    ['Leave one event out, range', f2(Math.min.apply(null, D.strategy_a.robustness.leave_one_out.filter(function (r) { return r.variant === 'A1'; }).map(function (r) { return r.sharpe; }))) + ' to ' + f2(Math.max.apply(null, D.strategy_a.robustness.leave_one_out.filter(function (r) { return r.variant === 'A1'; }).map(function (r) { return r.sharpe; }))),
      f2(Math.min.apply(null, D.strategy_a.robustness.leave_one_out.filter(function (r) { return r.variant === 'A2'; }).map(function (r) { return r.sharpe; }))) + ' to ' + f2(Math.max.apply(null, D.strategy_a.robustness.leave_one_out.filter(function (r) { return r.variant === 'A2'; }).map(function (r) { return r.sharpe; }))),
      f2(Math.min.apply(null, loo)) + ' to ' + f2(Math.max.apply(null, loo))],
    ['Share of date-shuffled draws beaten', Math.round(100 * pa.A1.share_beaten) + '%', Math.round(100 * pa.A2.share_beaten) + '%', Math.round(100 * pb.share_beaten) + '%']
  ];
  var tbl = $('tbl-robust-other');
  buildTable(tbl, ['Check (net Sharpe, 2024-2026)', 'A1', 'A2', 'PM-timed carry'], rows.map(function (r) { return [{ text: r[0], cls: 'txt' }, r[1], r[2], r[3]]; }));
  var tb = tbl.querySelector('tbody');
  Object.keys(post).forEach(function (name) {
    var h = post[name], tr = el('tr');
    tr.appendChild(el('td', { class: 'txt' }, [label(name) + ': actual ' + f2(h.actual) + ', beats ' + Math.round(100 * h.share_beaten) + '% of draws, random contracts ' + f2(h.random_contracts) + ', reversed ' + f2(h.reversed) + ' ', badge(h.status)]));
    tr.appendChild(el('td', { colspan: 3, text: '' }));
    tb.appendChild(tr);
  });
}

/* ================================================================== scrollytelling: the signal chain builds up as the reader scrolls */
var scrollyShow = null;
function scrolly() {
  var box = $('scrolly'), node = $('fig-scrolly');
  if (!box || !node) return;
  var W = D.walk, h = W.hazard_example, steps = box.querySelectorAll('.sc-step'), cur = -1;
  var x0 = h.dates[0], x1 = h.dates[h.dates.length - 1], cell = D.signals.cells['GLOBAL/GEOPOLITICS'];
  function clip(dates, arrs) {
    var out = { x: [] }; Object.keys(arrs).forEach(function (k) { out[k] = []; });
    dates.forEach(function (d, i) { if (d >= x0 && d <= x1) { out.x.push(d); Object.keys(arrs).forEach(function (k) { out[k].push(arrs[k][i]); }); } });
    return out;
  }
  var titles = ['A contract: the traded probability', 'Its implied hazard rate', 'Its standardised, signed daily changes', 'Averaged into the global geopolitics index',
                'Escalation: smoothed and z-scored', 'The exposure applied to the carry book', 'The same chain on the US monetary cell: Strategy A'];
  var states = [
    function () {
      return { traces: [{ type: 'scatter', mode: 'lines', x: h.dates, y: h.px.map(function (v) { return v == null ? null : 100 * v; }), name: 'probability', line: { color: T.neutral, width: 2 }, hovertemplate: '%{y:.0f}%<extra>probability</extra>' }],
               layout: { yaxis: { title: { text: 'probability (%)', font: { size: 12 } }, rangemode: 'tozero' } } };
    },
    function () {
      return { traces: [{ type: 'scatter', mode: 'lines', x: h.dates, y: h.px.map(function (v) { return v == null ? null : 100 * v; }), name: 'probability (%)', line: { color: T.axis, width: 1.5 }, hovertemplate: '%{y:.0f}%<extra>probability</extra>', yaxis: 'y2' },
                        { type: 'scatter', mode: 'lines', x: h.dates, y: h.hazard, name: 'hazard rate (per year)', line: { color: T.s[0], width: 2 }, hovertemplate: '%{y:.2f} a year<extra>hazard rate</extra>' }],
               legend: true, layout: { yaxis: { title: { text: 'hazard rate (per year)', font: { size: 12 } }, rangemode: 'tozero' }, yaxis2: { overlaying: 'y', side: 'right', showgrid: false, visible: false, rangemode: 'tozero' } } };
    },
    function () {
      return { traces: [{ type: 'bar', x: h.dates, y: h.z, name: 'z', marker: { color: h.z.map(function (v) { return v == null || v >= 0 ? T.pos : T.neg; }) }, hovertemplate: 'z = %{y:.2f}<extra></extra>' }],
               layout: { bargap: 0.2, hovermode: 'x', yaxis: { title: { text: 'z, signed (sd)', font: { size: 12 } }, zeroline: true, zerolinecolor: T.ink, range: [-5.3, 5.3] } } };
    },
    function () {
      var c = clip(D.signals.dates, { y: cell.index_vw, n: cell.n_contracts });
      return { traces: [{ type: 'scatter', mode: 'lines', x: c.x, y: c.y, name: 'global geopolitics index', line: { color: T.s[0], width: 2 }, hovertemplate: '%{y:.1f} sd<extra>index</extra>' },
                        { type: 'bar', x: c.x, y: c.n, name: 'contracts in the cell', yaxis: 'y2', marker: { color: T.seq[250] }, hovertemplate: '%{y} contracts<extra></extra>' }],
               legend: true, layout: { bargap: 0, yaxis: { domain: [0.32, 1], title: { text: 'index (sd)', font: { size: 12 } } }, yaxis2: { domain: [0, 0.24], gridcolor: T.grid, tickfont: { color: T.muted }, title: { text: 'contracts', font: { size: 11 } }, rangemode: 'tozero' } } };
    },
    function () {
      var c = clip(D.strategy_b.geo.dates, { z: D.strategy_b.geo.escalation_z }), cuts = D.meta.escalation_z_cuts;
      return { traces: [{ type: 'scatter', mode: 'lines', x: c.x, y: c.z, name: 'escalation z-score', line: { color: T.s[0], width: 2 }, hovertemplate: 'z = %{y:.2f}<extra>escalation</extra>' }],
               layout: { yaxis: { title: { text: 'escalation z-score', font: { size: 12 } }, zeroline: true, zerolinecolor: T.axis },
                         shapes: cuts.map(function (v) { return { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: v, y1: v, line: { color: T.s[1], width: 1 } }; }),
                         annotations: cuts.map(function (v, i) { return { xref: 'paper', yref: 'y', x: 0.01, y: v, text: 'month-end weight ' + (i === 0 ? D.meta.escalation_weights[1] : D.meta.escalation_weights[2]) + ' above ' + v, showarrow: false, xanchor: 'left', yanchor: 'bottom', font: { size: 11, color: T.ink2 } }; }) } };
    },
    function () {
      var c = clip(D.strategy_b.dates, { w: D.strategy_b.exposure.w, s: D.strategy_b.exposure.shock }), sx = [], sy = [];
      c.x.forEach(function (d, i) { if (c.s[i]) { sx.push(d); sy.push(c.w[i]); } });
      return { traces: [{ type: 'scatter', mode: 'lines', x: c.x, y: c.w, name: 'exposure w(t)', line: { color: T.s[0], width: 2, shape: 'hv' }, hovertemplate: 'w = %{y:.2f}<extra>exposure</extra>' },
                        { type: 'scatter', mode: 'markers', x: sx, y: sy, name: 'confirmed shock', marker: { size: 8, color: T.s[7], line: { color: T.surface, width: 2 } }, hovertemplate: 'shock<extra>%{x}</extra>' }],
               legend: true, layout: { yaxis: { range: [0, 1.06], title: { text: 'share of the carry position', font: { size: 12 } } } } };
    },
    function () {
      var c = clip(W.chain_a.dates, { z: W.chain_a.Z_mon, u: W.chain_a.usd_position });
      return { traces: [{ type: 'scatter', mode: 'lines', x: c.x, y: c.z, name: 'US monetary signal Z', line: { color: T.s[0], width: 2 }, hovertemplate: 'Z = %{y:.2f}<extra>US monetary</extra>' },
                        { type: 'bar', x: c.x, y: c.u, name: 'USD position (x capital)', yaxis: 'y2', marker: { color: c.u.map(function (v) { return v == null || v >= 0 ? T.pos : T.neg; }) }, hovertemplate: '%{y:.2f} x capital<extra>USD position</extra>' }],
               legend: true, layout: { bargap: 0, yaxis: { domain: [0.5, 1], title: { text: 'Z (sd)', font: { size: 12 } }, zeroline: true, zerolinecolor: T.axis },
                                       yaxis2: { domain: [0, 0.42], gridcolor: T.grid, tickfont: { color: T.muted }, title: { text: 'long (+) / short (-) USD', font: { size: 11 } }, zeroline: true, zerolinecolor: T.ink } } };
    }
  ];
  function show(i, force) {
    if (i === cur && !force) return;
    cur = i;
    steps.forEach(function (s, k) { s.classList.toggle('active', k === i); });
    var st = states[i]();
    $('sc-title').textContent = (i + 1) + '. ' + titles[i];
    $('sc-title').style.setProperty('--mc', getComputedStyle(steps[i]).getPropertyValue('--mc') || 'var(--s1)');
    plot('fig-scrolly', st.traces, merge({ xaxis: { range: [x0, x1] }, showlegend: !!st.legend, margin: { l: 50, r: 14, t: 8, b: 36 } }, st.layout || {}));
    if (MOTION) { node.classList.remove('reveal'); void node.offsetWidth; node.classList.add('reveal'); setTimeout(function () { node.classList.remove('reveal'); }, 1600); }
  }
  scrollyShow = function () { show(cur < 0 ? 0 : cur, true); };
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) show(Number(en.target.getAttribute('data-step'))); });
    }, { threshold: 0.5, rootMargin: '-8% 0px -8% 0px' });
    steps.forEach(function (s) { io.observe(s); });
  }
  show(0);
}

/* ================================================================== hero sparklines (inline SVG, themed by CSS classes) */
var NS = 'http://www.w3.org/2000/svg';
function svgEl(tag, attrs) { var e = document.createElementNS(NS, tag); Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); }); return e; }
function linePath(vals, x0, x1, y0, y1, lo, hi) {
  var n = vals.length, d = '';
  for (var i = 0; i < n; i++) { if (vals[i] == null) continue; var x = x0 + (x1 - x0) * i / (n - 1), y = y1 - (y1 - y0) * (vals[i] - lo) / (hi - lo || 1); d += (d ? ' L' : 'M') + x.toFixed(1) + ',' + y.toFixed(1); }
  return d;
}
function sparklines() {
  var W = 240, H = 58;
  var s1 = $('spark-timing'), s2 = $('spark-content'), s3 = $('spark-carry');
  if (s1) {   /* the hourly response of US monetary odds to the largest FX moves: a spike at hour 0, nothing before */
    var rows = D.timing.leadlag.rows.filter(function (r) { return r.study === 'FX top 1% -> PM US/MONETARY'; }).sort(function (a, b) { return a.hour - b.hour; });
    var v = rows.map(function (r) { return r.mean; }), lo = Math.min.apply(null, v.concat([0])), hi = Math.max.apply(null, v);
    var svg = svgEl('svg', { viewBox: '0 0 ' + W + ' ' + H });
    var i0 = rows.findIndex(function (r) { return r.hour === 0; }), x0 = 4 + (W - 8) * i0 / (rows.length - 1);
    svg.appendChild(svgEl('line', { x1: x0, y1: 4, x2: x0, y2: H - 14, class: 'hair' }));
    svg.appendChild(svgEl('path', { d: linePath(v, 4, W - 4, 6, H - 14, lo, hi), class: 'l1' }));
    svg.appendChild(svgEl('circle', { cx: x0, cy: H - 14 - (H - 20) * (v[i0] - lo) / (hi - lo || 1), r: 4, class: 'dot' }));
    [['h ' + rows[0].hour, 4, 'start'], ['hour of the FX move', x0, 'middle'], ['h +' + rows[rows.length - 1].hour, W - 4, 'end']].forEach(function (t) { var tx = svgEl('text', { x: t[1], y: H - 2, 'text-anchor': t[2] }); tx.textContent = t[0]; svg.appendChild(tx); });
    s1.appendChild(svg);
  }
  if (s2) {   /* coverage of the three kept cells against the gate */
    var kept = D.coverage.cells.filter(function (c) { return c.keep; }).sort(function (a, b) { return b.share_train - a.share_train; });
    var svg2 = svgEl('svg', { viewBox: '0 0 ' + W + ' ' + H }), gx = 4 + (W - 8) * D.coverage.gate;
    kept.forEach(function (c, i) {
      var y = 12 + i * 16, wbar = (W - 8) * c.share_train;
      svg2.appendChild(svgEl('rect', { x: 4, y: y, width: wbar, height: 9, rx: 2, class: 'bar' }));
      var tx = svgEl('text', { x: 9, y: y + 8, 'text-anchor': 'start', style: 'fill:#ffffff' });
      tx.textContent = c.zone + ' ' + (D.labels.theme[c.theme] || c.theme).toLowerCase() + ' ' + Math.round(100 * c.share_train) + '%'; svg2.appendChild(tx);
    });
    svg2.appendChild(svgEl('line', { x1: gx, y1: 8, x2: gx, y2: 58, class: 'hair' }));
    var gt = svgEl('text', { x: gx, y: 7, 'text-anchor': 'middle' }); gt.textContent = 'gate ' + Math.round(100 * D.coverage.gate) + '%'; svg2.appendChild(gt);
    s2.appendChild(svg2);
  }
  if (s3) {   /* base carry against the PM-timed overlay, net cumulative */
    var cb = D.strategy_b.cum_net, a = cb.base_carry, b = cb.pm_timed, all = a.concat(b).filter(function (x) { return x != null; });
    var lo3 = Math.min.apply(null, all), hi3 = Math.max.apply(null, all);
    var svg3 = svgEl('svg', { viewBox: '0 0 ' + W + ' ' + H });
    svg3.appendChild(svgEl('path', { d: linePath(a, 4, W - 4, 4, H - 14, lo3, hi3), class: 'l0' }));
    svg3.appendChild(svgEl('path', { d: linePath(b, 4, W - 4, 4, H - 14, lo3, hi3), class: 'l1' }));
    [['EM carry, base', 4, 'start'], ['with PM overlay', W - 4, 'end']].forEach(function (t) { var tx = svgEl('text', { x: t[1], y: H - 2, 'text-anchor': t[2] }); tx.textContent = t[0]; svg3.appendChild(tx); });
    s3.appendChild(svg3);
  }
}
/* the coverage gate sweeps from 0 to its value the first time the heatmap is seen, so the reader watches the cells switch on */
function gateSweep() {
  if (!MOTION || !$('tbl-coverage')) return;
  var target = state.gate, io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      io.disconnect();
      var t0 = null, dur = 1400;
      function step(now) {
        if (t0 == null) t0 = now;
        var p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 2);
        state.gate = Math.round(target * e); $('gate').value = state.gate; coverage();
        if (p < 1) requestAnimationFrame(step); else { state.gate = target; $('gate').value = target; coverage(); }
      }
      requestAnimationFrame(step);
    });
  }, { threshold: 0.4 });
  io.observe($('tbl-coverage'));
}

/* ================================================================== economic framework tabs and the progress rail */
function mechTabs() {
  var box = $('mech'); if (!box) return;
  var tabs = box.querySelectorAll('.mech-tab'), panels = box.querySelectorAll('.mech-panel');
  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      var m = t.getAttribute('data-m');
      tabs.forEach(function (x) { x.setAttribute('aria-selected', x === t ? 'true' : 'false'); });
      panels.forEach(function (p) { p.hidden = p.id !== 'mech-' + m; });
    });
  });
}
function rail() {
  var list = $('rail-list'), fill = $('rail-fill'); if (!list || !fill) return;
  var secs = Array.prototype.slice.call(document.querySelectorAll('main > section.sec'));
  var items = secs.map(function (s, i) {
    var a = document.querySelector('.nav a[href="#' + s.id + '"]');
    var li = el('li', {}, [el('a', { href: '#' + s.id, text: String(i + 1), 'data-title': (i + 1) + '. ' + (a ? a.textContent : s.id) })]);
    list.appendChild(li); return li;
  });
  function update() {
    var h = document.documentElement, p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
    fill.style.height = (100 * p).toFixed(1) + '%';
    var cur = -1; secs.forEach(function (s, i) { if (s.getBoundingClientRect().top <= window.innerHeight * 0.35) cur = i; });
    items.forEach(function (li, i) { li.classList.toggle('active', i === cur); li.classList.toggle('done', i < cur); });
  }
  window.addEventListener('scroll', update, { passive: true }); update();
}

/* ================================================================== theme */
function rethemeAll() { readTheme(); Object.keys(charts).forEach(redraw); if (scrollyShow) scrollyShow(); coverage(); horizon(); episodes(); conditional(); grid(); subperiods(); updateThemeBtn(); }
function currentTheme() { return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
function updateThemeBtn() { var b = $('theme-btn'); if (b) b.textContent = currentTheme() === 'dark' ? 'Light theme' : 'Dark theme'; }
function setTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  try { localStorage.setItem('theme', t); } catch (e) { /* private window or blocked storage: the choice just does not persist */ }
  rethemeAll();
}

/* ================================================================== wiring */
function init() {
  readTheme();
  updateThemeBtn();
  if ($('theme-btn')) $('theme-btn').addEventListener('click', function () { setTheme(currentTheme() === 'dark' ? 'light' : 'dark'); });
  /* 2 */
  $('hz-p').addEventListener('input', hazard); $('hz-tau').addEventListener('input', hazard);
  register('fig-hazard', hazard); register('fig-hazard-real', hazardReal); register('fig-class', classChart);
  walkTables(); scrolly();
  examples();
  /* 3 */
  $('gate').value = state.gate;
  $('gate').addEventListener('input', function () { state.gate = Number(this.value); coverage(); });
  seg('cov-period', function (v) { state.covPeriod = v; coverage(); });
  seg('cov-threshold', function (v) { state.covSet = v; coverage(); });
  coverage(); coverageFull();
  /* 4 */
  fillSelect($('sig-cell'), D.signals.order.map(function (k) { var c = D.signals.cells[k]; return { value: k, label: c.label + (c.kept ? ' (kept)' : '') }; }), state.sigCell);
  $('sig-cell').addEventListener('change', function () { state.sigCell = this.value; redraw('fig-signals'); });
  seg('sig-weight', function (v) { state.sigWeight = v; redraw('fig-signals'); });
  $('sig-ann').addEventListener('change', function () { state.sigAnn = this.checked; redraw('fig-signals'); });
  register('fig-signals', signals);
  /* 5 */
  horizon(); weekendTable();
  fillSelect($('ll-study'), D.timing.leadlag.studies.map(function (s) { return { value: s, label: s.replace('->', 'then').replace('PM ', 'prediction market ') }; }), state.llStudy);
  $('ll-study').addEventListener('change', function () { state.llStudy = this.value; redraw('fig-leadlag'); });
  register('fig-leadlag', leadlag);
  /* 6 */
  function aChips() { chipsFor('a-chips', D.strategy_a.variants.map(function (v) { return { id: v.id, label: v.label, color: colorA(v.id), status: v.status }; }), state.aSel, function (id) {
    var i = state.aSel.indexOf(id); if (i >= 0) { if (state.aSel.length > 1) state.aSel.splice(i, 1); } else state.aSel.push(id); aChips(); redraw('fig-a-cum'); }); }
  aChips();
  function setGross(v) { state.gross = v === 'gross'; ['gross-net', 'gross-net-b'].forEach(function (id) { $(id).querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-v') === v ? 'true' : 'false'); }); }); redraw('fig-a-cum'); redraw('fig-b-cum'); aCards(); bCards(); }
  seg('gross-net', setGross); seg('gross-net-b', setGross);
  $('a-ann').addEventListener('change', function () { state.aAnn = this.checked; redraw('fig-a-cum'); });
  register('fig-a-cum', aCum);
  fillSelect($('a-stat-variant'), D.strategy_a.variants.map(function (v) { return { value: v.id, label: v.label + (v.status !== 'pre-registered' ? ' (' + v.status + ')' : '') }; }), state.aStat);
  $('a-stat-variant').addEventListener('change', function () { state.aStat = this.value; aCards(); });
  seg('a-period', function (v) { state.aPeriod = v; aCards(); });
  aCards();
  register('fig-a-ladder', aLadder);
  seg('a-placebo-variant', function (v) { state.placeboA = v; redraw('fig-a-placebo'); });
  register('fig-a-placebo', aPlacebo);
  halflife(); register('fig-a-loo', aLoo); aRobustTable(); momentumTable(); gateTable();
  seg('d30-period', function (v) { state.d30 = v; redraw('fig-d30'); });
  register('fig-d30', d30); d30Tables();
  /* 7 */
  universeChips(); universeTable(); register('fig-lh', lh); register('fig-geo', geo);
  $('expo-vix').addEventListener('change', function () { state.expoVix = this.checked; redraw('fig-expo'); });
  register('fig-expo', expo);
  function bChips() { chipsFor('b-chips', D.strategy_b.lines.map(function (l) { return { id: l.id, label: l.label, color: colorB(l.id), status: l.status, dashed: l.id === 'pm_timed_without_event' }; }), state.bSel, function (id) {
    var i = state.bSel.indexOf(id); if (i >= 0) { if (state.bSel.length > 1) state.bSel.splice(i, 1); } else state.bSel.push(id); bChips(); redraw('fig-b-cum'); }); }
  bChips();
  $('b-ann').addEventListener('change', function () { state.bAnn = this.checked; redraw('fig-b-cum'); });
  register('fig-b-cum', bCum);
  fillSelect($('b-stat-line'), D.strategy_b.lines.filter(function (l) { return l.id !== 'pm_timed_without_event'; }).map(function (l) { return { value: l.id, label: l.label + (l.status !== 'pre-registered' ? ' (' + l.status + ')' : '') }; }), state.bStat);
  $('b-stat-line').addEventListener('change', function () { state.bStat = this.value; bCards(); });
  seg('b-period', function (v) { state.bPeriod = v; bCards(); });
  $('b-taiwan').addEventListener('change', function () { state.taiwan = this.checked; bCards(); });
  bCards();
  register('fig-b-keymonth', keyMonth); register('fig-b-ladder', bLadder); register('fig-b-comp', composition);
  /* 8 */
  episodes();
  var riskStrategies = []; D.risk.betas.forEach(function (r) { if (riskStrategies.indexOf(r.strategy) < 0) riskStrategies.push(r.strategy); });
  fillSelect($('beta-strategy'), riskStrategies.map(function (s) { return { value: s, label: label(s) }; }), 'base_carry');
  $('beta-strategy').addEventListener('change', function () { redraw('fig-betas'); });
  register('fig-betas', betas);
  $('down-market').addEventListener('change', function () { redraw('fig-downside'); });
  register('fig-downside', downside);
  var conds = []; D.risk.conditional.forEach(function (r) { if (conds.indexOf(r.conditioner) < 0) conds.push(r.conditioner); });
  fillSelect($('cond-select'), conds.map(function (c) { return { value: c, label: c }; }), conds.indexOf('half-spread tercile') >= 0 ? 'half-spread tercile' : conds[0]);
  $('cond-select').addEventListener('change', conditional); conditional();
  var ddS = []; D.risk.worst_drawdowns.forEach(function (r) { if (ddS.indexOf(r.strategy) < 0) ddS.push(r.strategy); });
  fillSelect($('dd-strategy'), ddS.map(function (s) { return { value: s, label: label(s) }; }), 'A1_theory_with_dollar');
  $('dd-strategy').addEventListener('change', worstDD); worstDD(); concentration(); leverage();
  /* 9 */
  var pl = [{ value: 'A1', label: 'A1' }, { value: 'A2', label: 'A2' }, { value: 'A1+S', label: 'A1 + geopolitics' }, { value: 'B', label: 'PM-timed carry' }].concat(Object.keys(D.robustness.posthoc).map(function (k) { return { value: k, label: label(k) + ' (' + D.robustness.posthoc[k].status + ')' }; }));
  fillSelect($('placebo-select'), pl, 'B');
  $('placebo-select').addEventListener('change', function () { redraw('fig-placebo'); });
  register('fig-placebo', placeboAll);
  var cutBox = $('grid-cut'); D.meta.shock_cut_grid.forEach(function (c) { var b = el('button', { type: 'button', 'data-v': String(c), 'aria-pressed': c === state.gridCut ? 'true' : 'false', text: 'cut to ' + Math.round(100 * c) + '%' }); cutBox.appendChild(b); });
  seg('grid-cut', function (v) { state.gridCut = Number(v); grid(); });
  grid(); register('fig-cost', cost); subperiods(); robustOther();

  /* lazy drawing of the charts as they approach the viewport */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) { entries.forEach(function (en) { if (en.isIntersecting) { var id = en.target.id; if (charts[id] && !charts[id].done) draw(id); io.unobserve(en.target); } }); }, { rootMargin: '600px 0px' });
    Object.keys(charts).forEach(function (id) { if (charts[id].node) io.observe(charts[id].node); });
  } else Object.keys(charts).forEach(draw);

  /* navigation */
  var links = document.querySelectorAll('.nav a'), secs = Array.prototype.map.call(links, function (a) { return $(a.getAttribute('href').slice(1)); });
  function onScroll() {
    var h = document.documentElement, p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
    $('progress').style.width = (100 * p).toFixed(1) + '%';
    var cur = -1; secs.forEach(function (s, i) { if (s && s.getBoundingClientRect().top <= 80) cur = i; });
    links.forEach(function (a, i) { a.classList.toggle('active', i === cur); });
  }
  window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
  setupReveal(); observeCounts(document); sparklines(); gateSweep(); mechTabs(); rail();
  glossary('tbl-a-glossary', D.strategy_a.variants); glossary('tbl-b-glossary', D.strategy_b.lines);
  if ($('expo-play')) $('expo-play').addEventListener('click', togglePlay);
  $('tbl-grid').addEventListener('click', function (ev) { var td = ev.target.closest('td.cell.pick'); if (td) gridPick(td); });
  var resizeTimer;
  function resizeAll() { Object.keys(charts).forEach(function (id) { if (charts[id].done && charts[id].node) Plotly.Plots.resize(charts[id].node); }); }
  window.addEventListener('orientationchange', function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(function () { readTheme(); Object.keys(charts).forEach(redraw); }, 250); });
  window.addEventListener('resize', function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(resizeAll, 150); });
  if (window.matchMedia) { var mq = window.matchMedia('(prefers-color-scheme: dark)'); if (mq.addEventListener) mq.addEventListener('change', rethemeAll); }
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
