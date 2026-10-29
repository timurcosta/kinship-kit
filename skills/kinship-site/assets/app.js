/* Живая версия семейного отчёта: карта, путь по датам, документы, хронология, поиск, версии.
   Данные: window.STORY (story.json), GALLERY, TIMELINE, GEO — собирает build_web.py скилла kinship-site. */
(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const S = window.STORY, G = window.GALLERY || [], T = window.TIMELINE || [], U = window.UI || {};
  const t = (k, o = {}) => String(U[k] == null ? k : U[k]).replace(/\{(\w+)\}/g, (m, x) => o[x] == null ? m : o[x]);
  const pl = (n, f) => (n % 10 === 1 && n % 100 !== 11) ? f[0] : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) ? f[1] : f[2];
  const P = S.player || {}, YEAR = P.year || '';
  const TAGS = { ok: t('tagOk'), maybe: t('tagMaybe'), fam: t('tagFam'), no: t('tagNo') };
  /* family lines: a site may hold several (father's, mother's); the switch shows one line at a time.
     Views without "line" are shared and show every line's places. */
  const LINES = window.LINES || null, LC = {};
  (LINES || []).forEach(l => LC[l.key] = l.color);
  let line = LINES ? LINES[0].key : null;
  try { const s = localStorage.getItem('kinship-line'); if (LINES && LC[s]) line = s; } catch (e) { }
  const vis = it => !LINES || !it.line || it.line === line;
  const viewKeys = () => Object.keys(S.views).filter(k => vis(S.views[k]));
  const FIRST = viewKeys()[0];
  const steps = () => (S.steps || []).filter(vis);
  const PL = () => Object.assign({}, P, (P.byLine || {})[line] || {});
  const PAGE = U.secSuffix ? `${U.lang}.html` : '';   // a language page other than index.html
  let rerunSearch = null;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const tagHtml = t => t ? `<span class="tag ${t}">${TAGS[t]}</span>` : '';

  /* ---------------- lightbox ---------------- */
  const LB = (() => {
    const el = $('#lb'), stage = $('.lb-stage', el), img = $('img', stage), cap = $('.lb-cap', el),
      count = $('.count', el), orig = $('.lb-orig', el);
    let list = [], i = 0, s = 1, x = 0, y = 0, fit = 1;
    const ptrs = new Map(); let pinch0 = null, drag0 = null, tapT = 0, swipe0 = null;
    function apply() { img.style.transform = `translate(${x}px,${y}px) scale(${s})`; }
    function reset() {
      const W = stage.clientWidth, H = stage.clientHeight, w = img.naturalWidth || 1, h = img.naturalHeight || 1;
      fit = Math.min(W / w, H / h, 1.6); s = fit; x = -w * s / 2; y = -h * s / 2; apply();
    }
    function zoomAt(f, cx, cy) {
      const r = stage.getBoundingClientRect(), px = cx - r.left - r.width / 2, py = cy - r.top - r.height / 2;
      const ns = Math.max(fit * 0.8, Math.min(s * f, fit * 12));
      x = px - (px - x) * (ns / s); y = py - (py - y) * (ns / s); s = ns; apply();
    }
    function show(k) {
      i = (k + list.length) % list.length; const it = list[i];
      img.onload = reset; img.src = it.src; cap.innerHTML = it.cap || '';
      count.textContent = list.length > 1 ? t('nOfM', { i: i + 1, n: list.length }) : '';
      orig.href = it.full || it.src; orig.style.display = it.full ? '' : 'none';
      $$('.side', el).forEach(b => b.style.display = list.length > 1 ? '' : 'none');
    }
    function open(items, k = 0) { list = items; el.classList.add('on'); document.body.style.overflow = 'hidden'; show(k); }
    function close() { el.classList.remove('on'); document.body.style.overflow = ''; img.removeAttribute('src'); }
    $('.lb-close', el).onclick = close;
    $('.prev', el).onclick = () => show(i - 1);
    $('.next', el).onclick = () => show(i + 1);
    $('.lb-in', el).onclick = () => { const r = stage.getBoundingClientRect(); zoomAt(1.5, r.left + r.width / 2, r.top + r.height / 2); };
    $('.lb-out', el).onclick = () => { const r = stage.getBoundingClientRect(); zoomAt(1 / 1.5, r.left + r.width / 2, r.top + r.height / 2); };
    $('.lb-fit', el).onclick = reset;
    window.addEventListener('resize', () => el.classList.contains('on') && reset());
    document.addEventListener('keydown', e => {
      if (!el.classList.contains('on')) return;
      if (e.key === 'Escape') close(); else if (e.key === 'ArrowLeft') show(i - 1); else if (e.key === 'ArrowRight') show(i + 1);
      else if (e.key === '+' || e.key === '=') $('.lb-in', el).click(); else if (e.key === '-') $('.lb-out', el).click();
    });
    stage.addEventListener('wheel', e => { e.preventDefault(); zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX, e.clientY); }, { passive: false });
    stage.addEventListener('pointerdown', e => {
      stage.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]);
      if (ptrs.size === 1) { drag0 = [e.clientX - x, e.clientY - y]; swipe0 = [e.clientX, e.clientY, Date.now()]; }
      if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; pinch0 = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), s }; }
    });
    stage.addEventListener('pointermove', e => {
      if (!ptrs.has(e.pointerId)) return; ptrs.set(e.pointerId, [e.clientX, e.clientY]);
      if (ptrs.size === 2 && pinch0) {
        const [a, b] = [...ptrs.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        zoomAt((pinch0.s * d / pinch0.d) / s, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2);
      } else if (ptrs.size === 1 && drag0 && s > fit * 1.02) { x = e.clientX - drag0[0]; y = e.clientY - drag0[1]; apply(); }
    });
    const up = e => {
      if (!ptrs.has(e.pointerId)) return; ptrs.delete(e.pointerId);
      if (ptrs.size < 2) pinch0 = null;
      if (ptrs.size === 0 && swipe0) {
        const dx = e.clientX - swipe0[0], dy = e.clientY - swipe0[1], dt = Date.now() - swipe0[2];
        if (s <= fit * 1.02 && Math.abs(dx) > 60 && Math.abs(dy) < 50 && dt < 500 && list.length > 1) show(i + (dx < 0 ? 1 : -1));
        else if (Math.abs(dx) < 6 && Math.abs(dy) < 6) {
          if (Date.now() - tapT < 300) { s > fit * 1.05 ? reset() : zoomAt(2.5, e.clientX, e.clientY); tapT = 0; } else tapT = Date.now();
        }
        swipe0 = null; drag0 = null;
      } else if (ptrs.size === 1) { const p = [...ptrs.values()][0]; drag0 = [p[0] - x, p[1] - y]; }
    };
    stage.addEventListener('pointerup', up); stage.addEventListener('pointercancel', up);
    el.addEventListener('click', e => { if (e.target === el) close(); });
    return { open };
  })();
  const docItem = src => G.find(g => g.src === src) || { src, cap: '' };

  /* ---------------- glyphs ---------------- */
  const GLYPH = {
    home: '<path d="M-5,0.5 L0,-4.5 L5,0.5 M-3.4,-0.6 V4.4 H3.4 V-0.6" stroke="#fff" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
    birth: '<polygon points="0,-5 1.3,-1.8 4.8,-1.5 2.1,0.7 3,4.1 0,2.3 -3,4.1 -2.1,0.7 -4.8,-1.5 -1.3,-1.8" fill="#fff"/>',
    missing: '<text x="0" y="4.3" font-size="12" font-weight="700" text-anchor="middle" fill="#fff" font-family="Arial">?</text>',
    death: '<path d="M0,-5 V5 M-3.6,-1.8 H3.6" stroke="#fff" stroke-width="1.9" stroke-linecap="round"/>',
    pow: '<circle cx="-3" cy="-1.6" r="2.4" stroke="#fff" stroke-width="1.8" fill="none"/><rect x="-1.95" y="-4.65" width="2.3" height="1.7" rx=".45" fill="#fff" transform="rotate(-40 -0.8 -3.8)"/><circle cx="1.05" cy="-4.75" r=".95" stroke="#fff" stroke-width=".85" fill="none"/><circle cx="2.75" cy="-3.3" r=".95" stroke="#fff" stroke-width=".85" fill="none"/><circle cx="3" cy="2.5" r="2.4" stroke="#fff" stroke-width="1.8" fill="none"/><rect x="1.9" y="-1.85" width="2.2" height="1.7" rx=".45" fill="#fff" transform="rotate(10 3 -1)"/>',
    division: '<path d="M-3,5 V-5" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/><path d="M-3,-5 L4.5,-2.6 L-3,-0.2 Z" fill="#fff"/>',
    event: '<polygon points="0,-5.2 1.3,-2.3 4.5,-2.6 2.6,0 4.5,2.6 1.3,2.3 0,5.2 -1.3,2.3 -4.5,2.6 -2.6,0 -4.5,-2.6 -1.3,-2.3" fill="#fff"/>',
    station: '<rect x="-4" y="-4.5" width="8" height="7" rx="1.5" fill="#fff"/><circle cx="-2.2" cy="4" r="1.2" fill="#fff"/><circle cx="2.2" cy="4" r="1.2" fill="#fff"/>',
  };
  const pinHtml = (kind, approx, cls = '', lineKey = '') => {
    const c = S.kinds[kind].color;
    const ring = lineKey && LC[lineKey] ? `;box-shadow:0 0 0 2.5px ${LC[lineKey]},0 1px 4px rgba(0,0,0,.35)` : '';
    if (kind === 'ref') return `<div class="pin ref ${cls}" style="background:${c}"></div>`;
    return `<div class="pin ${approx ? 'approx' : ''} ${cls}" style="background:${c};color:${c}${ring}"><svg viewBox="-7 -7 14 14">${GLYPH[kind]}</svg></div>`;
  };

  /* ---------------- map ---------------- */
  let map, view = FIRST, markers = {}, hidden = new Set(), routeLayer, stepLayer, frontLayer;
  function initMap() {
    if (!window.L || !$('#map')) return;
    map = L.map('map', { zoomSnap: 0.25, attributionControl: true, worldCopyJump: false, minZoom: 4, maxZoom: 13, zoomControl: true });
    map.attributionControl.setPrefix(false).addAttribution('Natural Earth · © OpenStreetMap');
    const g = window.GEO;
    L.geoJSON(g.water, { interactive: false, style: { stroke: true, color: '#9fbfd6', weight: 0.8, fillColor: '#cfe0ea', fillOpacity: 1 } }).addTo(map);
    const big = L.geoJSON(g.riversNamed, { interactive: false, style: { color: '#6f9bbb', weight: 1.8 } }).addTo(map);
    const small = L.geoJSON(g.riversOther, { interactive: false, style: { color: '#8db0c8', weight: 1 } });
    const riverLbls = L.layerGroup((S.riverLabels || g.riverLabels || []).map(r => L.tooltip({ permanent: true, direction: 'center', className: 'lbl river', interactive: false }).setLatLng([r[1], r[2]]).setContent(r[0])));
    const syncZoom = () => {
      const z = map.getZoom();
      if (z >= 7.5) small.addTo(map); else small.remove();
      if (z >= 6.5) riverLbls.addTo(map); else riverLbls.remove();
      $('#map').classList.toggle('zoomed', z >= 8);
      Object.values(markers).forEach(m => { const t = m.getTooltip(); if (t && m.options.kind === 'ref') { z >= 7 ? m.openTooltip() : m.closeTooltip(); } });
    };
    map.on('zoomend', syncZoom);
    map.fitBounds(S.views[FIRST].bounds, { padding: [10, 10] });
    frontLayer = L.layerGroup().addTo(map); routeLayer = L.layerGroup().addTo(map); stepLayer = L.layerGroup().addTo(map);
    S.places.forEach(p => {
      const m = L.marker([p.lat, p.lon], {
        kind: p.kind, keyboard: true, title: p.kind === 'ref' ? p.name : `${p.name} — ${S.kinds[p.kind].label}`, riseOnHover: true,
        icon: L.divIcon({ className: '', html: pinHtml(p.kind, p.approx, '', p.line), iconSize: p.kind === 'ref' ? [10, 10] : [30, 30], iconAnchor: p.kind === 'ref' ? [5, 5] : [15, 15], popupAnchor: [0, -14] }),
      });
      const dir = p.dir || 'right', o = p.kind === 'ref' ? 6 : 14;
      const off = { right: [o, 0], left: [-o, 0], top: [0, -o], bottom: [0, o] }[dir];
      const nm = (window.innerWidth < 720 && p.short) ? p.short : p.name;
      m.bindTooltip(nm, { permanent: true, direction: dir, offset: off, className: 'lbl' + (p.kind === 'ref' ? ' ref' : '') });
      m.bindPopup(() => popupHtml(p), { maxWidth: 320, autoPanPadding: [20, 70] });
      m.on('popupopen', e => $$('.docbtn', e.popup.getElement()).forEach(b => b.onclick = () => LB.open([docItem(b.dataset.src)])));
      markers[p.key] = m;
    });
    // kind filter chips
    const chips = $('#kind-chips');
    Object.entries(S.kinds).forEach(([k, v]) => {
      const b = document.createElement('button'); b.className = 'chip'; b.dataset.kind = k;
      b.innerHTML = `<i style="background:${v.color}"></i>${v.label}`;
      b.onclick = () => { hidden.has(k) ? hidden.delete(k) : hidden.add(k); b.classList.toggle('off'); drawView(false); };
      chips.appendChild(b);
    });
    $$('#map-tabs .tab').forEach(b => b.onclick = () => { setView(b.dataset.view, true); });
    $$('#map-tabs .tab').forEach(b => b.hidden = !vis(S.views[b.dataset.view]));
    setView(FIRST, true);
    setTimeout(syncZoom, 50);
  }
  function popupHtml(p) {
    const k = S.kinds[p.kind];
    const evs = (p.events || []).map(e => `<div class="ev">${e.date ? `<span class="d">${esc(e.date)}</span> · ` : ''}${esc(e.text)} ${tagHtml(e.tag)}
      ${e.img ? `<br><button class="docbtn" data-src="${e.img}">${t('openDoc')}</button>` : ''}</div>`).join('');
    return `<div class="pop"><h4>${esc(p.name)}</h4><div class="k">${k.label}${p.approx ? t('approx') : ''}</div>${evs || ''}</div>`;
  }
  function curve(a, b) {
    const pts = [], k = Math.cos((a[0] + b[0]) / 2 * Math.PI / 180);
    const dx = (b[1] - a[1]) * k, dy = b[0] - a[0];
    const c = [(a[0] + b[0]) / 2 + dx * 0.12, (a[1] + b[1]) / 2 - dy * 0.12 / k];
    for (let t = 0; t <= 1.0001; t += 0.05) pts.push([(1 - t) * (1 - t) * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0], (1 - t) * (1 - t) * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]]);
    return pts;
  }
  function drawView(fit) {
    Object.entries(markers).forEach(([key, m]) => {
      const p = S.places.find(x => x.key === key);
      const on = p.views.includes(view) && !hidden.has(p.kind);
      on ? m.addTo(map) : m.remove();
      m.setOpacity(vis(p) ? 1 : 0.4);   // on a shared view the other line stays visible, but quieter
    });
    routeLayer.clearLayers(); stepLayer.clearLayers(); drawFront();
    if (!hidden.has('division')) S.routes.filter(r => r.view === view).forEach(r => {
      const pts = r.stops.map(k => S.places.find(p => p.key === k));
      const dim = vis(r) ? 1 : 0.35;
      pts.forEach((p, n) => L.marker([p.lat, p.lon], { interactive: false, opacity: dim, icon: L.divIcon({ className: '', html: `<div class="stepno"${LC[r.line] ? ` style="color:${LC[r.line]};border-color:${LC[r.line]}"` : ''}>${n + 1}</div>`, iconSize: [20, 20], iconAnchor: [-6, 26] }) }).addTo(stepLayer));
      for (let n = 0; n < pts.length - 1; n++) {
        const line = curve([pts[n].lat, pts[n].lon], [pts[n + 1].lat, pts[n + 1].lon]);
        const cut = line.slice(2, -2);
        L.polyline(cut, { color: '#fff', weight: 8, opacity: .8 * dim, interactive: false }).addTo(routeLayer);
        const rl = L.polyline(cut, { color: LC[r.line] || '#7a2e1f', weight: 4, opacity: dim, className: 'route', interactive: false }).addTo(routeLayer);
        const el = rl.getElement(); if (el) el.setAttribute('marker-end', LC[r.line] ? `url(#arrowhead-${r.line})` : 'url(#arrowhead)');
      }
    });
    if (fit) { if (map._loaded) map.flyToBounds(S.views[view].bounds, { duration: 0.6, padding: [10, 10] }); else map.fitBounds(S.views[view].bounds, { padding: [10, 10] }); }
  }
  /* front: German thrusts as tapered arrows, the pocket, the breakout. Shapes are drawn in km so they scale with zoom. */
  const TANK = '<svg viewBox="0 0 24 24" fill="#fff"><rect x="3" y="13" width="18" height="5" rx="2.5"/><rect x="7" y="9" width="8" height="5" rx="1.5"/><rect x="14" y="10.4" width="8" height="1.8" rx=".9"/><circle cx="6.5" cy="15.5" r="1" fill="#1f3f73"/><circle cx="10.5" cy="15.5" r="1" fill="#1f3f73"/><circle cx="14.5" cy="15.5" r="1" fill="#1f3f73"/><circle cx="18" cy="15.5" r="1" fill="#1f3f73"/></svg>';
  function km(path) {
    const kx = 111.32 * Math.cos(path[0][0] * Math.PI / 180), ky = 110.57;
    return { P: path.map(([la, lo]) => [lo * kx, la * ky]), back: ([x, y]) => [y / ky, x / kx] };
  }
  function spline(P, closed) {
    const n = P.length, out = [], at = i => closed ? P[(i + n) % n] : P[Math.max(0, Math.min(n - 1, i))];
    for (let i = 0; i < (closed ? n : n - 1); i++) {
      const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
      for (let t = 0; t < 1; t += 0.08) {
        const t2 = t * t, t3 = t2 * t;
        out.push([0, 1].map(k => 0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)));
      }
    }
    if (!closed) out.push(P[n - 1]);
    return out;
  }
  function along(pts, f) {
    const L = [0]; for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const s = L[L.length - 1] * f; let i = 1; while (i < L.length - 1 && L[i] < s) i++;
    const r = (s - L[i - 1]) / ((L[i] - L[i - 1]) || 1);
    return { L, pt: [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * r, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * r], i };
  }
  function fatArrow(path, w0, w1, headW, headL) {
    // body widens from w0 to w1, then the head narrows from headW to the tip along the same curve, so bends never kink
    const { P, back } = km(path), pts = spline(P, false);
    const { L } = along(pts, 1), total = L[L.length - 1], hl = Math.min(headL, total * 0.35), sb = total - hl, base = along(pts, sb / total);
    const dir = (a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy) || 1; return [-dy / d, dx / d]; };
    const at = i => dir(pts[Math.max(0, i - 1)], pts[Math.min(pts.length - 1, i + 1)]);
    const seq = [];
    pts.forEach((p, i) => { if (L[i] < sb) seq.push([p, w0 + (w1 - w0) * L[i] / sb, at(i)]); });
    const nb = dir(pts[base.i - 1], pts[base.i]);
    seq.push([base.pt, w1, nb], [base.pt, headW, nb]);
    pts.forEach((p, i) => { if (L[i] > sb) seq.push([p, headW * (total - L[i]) / hl, at(i)]); });
    const left = seq.map(([p, w, n]) => [p[0] + n[0] * w / 2, p[1] + n[1] * w / 2]);
    const right = seq.map(([p, w, n]) => [p[0] - n[0] * w / 2, p[1] - n[1] * w / 2]);
    return left.concat(right.reverse()).map(back);
  }
  function frontPopup(f) {
    return `<div class="pop"><h4>${esc(f.label)}</h4><div class="ev">${esc(f.text)}</div><div class="k">${t('source')} ${esc(f.src)} ${tagHtml(f.tag)}</div></div>`;
  }
  function drawFront() {
    frontLayer.clearLayers();
    const narrow = window.innerWidth < 720;
    (S.front || []).filter(f => f.view === view).forEach(f => {
      if (f.type !== 'escape' && hidden.has('enemy')) return;
      if (f.type === 'escape' && hidden.has('division')) return;
      const name = narrow && f.short ? f.short : f.label;
      if (f.type === 'thrust') {
        const k = f.scale || 1;   // arrow size in km: smaller for a close-up view
        L.polygon(fatArrow(f.path, 4 * k, 10 * k, 30 * k, 22 * k), { color: '#fff', weight: 1.5, fillColor: '#1f3f73', fillOpacity: .5, className: 'thrust' })
          .bindPopup(frontPopup(f), { maxWidth: 320 }).addTo(frontLayer);
        const { P, back } = km(f.path), at = back(along(spline(P, false), f.at || 0.25).pt);
        L.marker(at, { icon: L.divIcon({ className: '', html: `<div class="tank" title="${esc(f.label)}">${TANK}</div>`, iconSize: [28, 28], iconAnchor: [14, 14], popupAnchor: [0, -12] }) })
          .bindTooltip(name, { permanent: true, direction: f.dir || 'right', offset: f.dir === 'top' ? [0, -14] : [14, 0], className: 'lbl enemy' })
          .bindPopup(frontPopup(f), { maxWidth: 320 }).addTo(frontLayer);
      } else if (f.type === 'pocket') {
        const { P, back } = km(f.ring);
        L.polygon(spline(P, true).map(back), { color: '#c0392b', weight: 2.5, dashArray: '7 6', fillColor: '#c0392b', fillOpacity: .1, className: 'pocket' })
          .bindPopup(frontPopup(f), { maxWidth: 320 }).addTo(frontLayer);
        L.marker(narrow && f.centerNarrow || f.center, { icon: L.divIcon({ className: '', html: `<div class="pocket-lbl">${esc(name)}${f.date ? `<small>${esc(f.date)}</small>` : ''}</div>`, iconSize: [0, 0] }) })
          .bindPopup(frontPopup(f), { maxWidth: 320 }).addTo(frontLayer);
      } else if (f.type === 'escape') {
        const { P, back } = km(f.path), pts = spline(P, false).map(back);
        L.polyline(pts, { color: '#fff', weight: 6, opacity: .8, interactive: false }).addTo(frontLayer);
        const pl = L.polyline(pts, { color: '#7a2e1f', weight: 2.5, dashArray: '2 6', lineCap: 'round', className: 'escape' }).bindPopup(frontPopup(f), { maxWidth: 320 }).addTo(frontLayer);
        const el = pl.getElement(); if (el) el.setAttribute('marker-end', 'url(#arrowhead)');
        L.marker(back(along(spline(P, false), f.at || 0.5).pt), { interactive: false, icon: L.divIcon({ className: '', html: '', iconSize: [0, 0] }) })
          .bindTooltip(name, { permanent: true, direction: f.dir || 'right', offset: { right: [8, 0], left: [-8, 0], top: [0, -8], bottom: [0, 8] }[f.dir || 'right'], className: 'lbl escape' }).addTo(frontLayer);
      }
    });
  }
  function setView(v, fit) {
    if (LINES && S.views[v].line && S.views[v].line !== line) setLine(S.views[v].line, true);
    view = v; $$('#map-tabs .tab').forEach(b => b.classList.toggle('on', b.dataset.view === v)); drawView(fit);
  }

  /* ---------------- division path player ---------------- */
  let cur = -1, timer = null;
  function initPlayer() {
    const wrap = $('#steps'); if (!wrap || !S.steps) return;
    renderSteps();
    $('#step-prev').onclick = () => goStep(Math.max(0, cur - 1), true);
    $('#step-next').onclick = () => goStep(Math.min(steps().length - 1, cur + 1), true);
    $('#step-play').onclick = () => {
      if (timer) { stopPlay(); return; }
      $('#step-play').textContent = t('pause');
      if (cur >= steps().length - 1) cur = -1;
      goStep(cur + 1, true); timer = setInterval(() => { cur >= steps().length - 1 ? stopPlay() : goStep(cur + 1, true); }, 6500);
    };
  }
  function renderSteps() {
    const wrap = $('#steps'); if (!wrap) return;
    wrap.innerHTML = ''; $('#player').hidden = !steps().length;
    const h = $('#player h3'); if (h && PL().title) h.textContent = PL().title;
    if (!steps().length) return;
    steps().forEach((st, n) => {
      const b = document.createElement('button'); b.textContent = st.date; b.title = st.title; b.onclick = () => goStep(n, true); wrap.appendChild(b);
    });
    renderStep(0);
  }
  function stopPlay() { clearInterval(timer); timer = null; $('#step-play').textContent = t('play'); }
  function renderStep(n) {
    cur = n; const st = steps()[n], yr = PL().year || '';
    $$('#steps button').forEach((b, k) => { b.classList.toggle('on', k === n); b.classList.toggle('done', k < n); });
    const btn = $$('#steps button')[n], wrap = $('#steps');   // scroll only the strip of dates, never the page
    if (btn) wrap.scrollTo({ left: btn.offsetLeft - wrap.offsetLeft - (wrap.clientWidth - btn.offsetWidth) / 2, behavior: 'smooth' });
    $('#step-card').innerHTML = `<div class="d">${esc(st.date)}${yr ? ' ' + yr : ''}</div><h4>${esc(st.title)}</h4><p>${esc(st.text)}</p>
      <blockquote>${esc(st.quote)}</blockquote><div class="src">${esc(st.src)} ${tagHtml(st.tag)}</div>
      ${st.img ? `<img class="thumb" src="${(docItem(st.img).thumb || docItem(st.img).src)}" alt="${t('docAlt')} ${esc(st.src)}">` : ''}`;
    const th = $('#step-card .thumb'); if (th) th.onclick = () => LB.open([docItem(st.img)]);
    $('#step-count').textContent = `${n + 1} / ${steps().length}`;
  }
  function goStep(n, move) {
    renderStep(n); const st = steps()[n];
    if (!map) return;
    if (view !== st.view) setView(st.view, false);
    $$('.pin.pulse').forEach(e => e.classList.remove('pulse'));
    const pts = st.focus.map(k => S.places.find(p => p.key === k)).filter(Boolean);
    pts.forEach(p => { const el = markers[p.key] && markers[p.key].getElement(); if (el) { const pin = $('.pin', el); pin && pin.classList.add('pulse'); } });
    if (move && pts.length) {
      const b = L.latLngBounds(pts.map(p => [p.lat, p.lon]));
      const narrow = window.innerWidth < 720;
      map.flyToBounds(b.pad(pts.length > 1 ? 0.3 : 0), { maxZoom: narrow ? 8.5 : 9.5, duration: 0.8, padding: narrow ? [28, 28] : [40, 40] });
    }
  }

  /* ---------------- gallery ---------------- */
  const ALL = t('all');
  let galFilter = ALL, galQuery = '';
  function initGallery() {
    const box = $('#gal'), chips = $('#gal-chips'); if (!box) return;
    chips.innerHTML = ''; galFilter = ALL;
    const groups = [ALL, ...new Set(G.filter(g => g.inGallery && vis(g)).map(g => g.grp))];
    groups.forEach(gname => {
      const b = document.createElement('button'); b.className = 'tab' + (gname === ALL ? ' on' : ''); b.textContent = gname;
      b.onclick = () => { galFilter = gname; $$('.tab', chips).forEach(x => x.classList.toggle('on', x === b)); renderGallery(); };
      chips.appendChild(b);
    });
    renderGallery();
  }
  function galItems() {
    const q = galQuery.toLowerCase();
    return G.filter(g => g.inGallery && vis(g) && (galFilter === ALL || g.grp === galFilter) && (!q || (g.text || '').toLowerCase().includes(q)));
  }
  function renderGallery() {
    const box = $('#gal'), items = galItems();
    box.innerHTML = items.length ? '' : `<div class="gal-empty">${t('nothing')}</div>`;
    items.forEach((g, n) => {
      const b = document.createElement('button'); b.className = 'item card';
      b.innerHTML = `<img loading="lazy" src="${g.thumb || g.src}" alt=""><div class="cap">${esc(g.text || '')}</div><div class="grp">${esc(g.grp)}</div>`;
      b.onclick = () => LB.open(items, n); box.appendChild(b);
    });
    $('#gal-count').textContent = `${items.length} ${pl(items.length, U.docForms || ['документ', 'документа', 'документов'])}`;
  }

  /* ---------------- timeline ---------------- */
  let tlFilter = 'all';
  function initTimeline() {
    const box = $('#tl'), chips = $('#tl-chips'); if (!box) return;
    chips.innerHTML = ''; tlFilter = 'all';
    [['all', t('everything')], ['ok', TAGS.ok], ['fam', TAGS.fam], ['maybe', TAGS.maybe], ['war', PL().label || t('stepsLabel')]].filter(([k]) => k !== 'war' || steps().length).forEach(([k, l]) => {
      const b = document.createElement('button'); b.className = 'tab' + (k === 'all' ? ' on' : ''); b.textContent = l;
      b.onclick = () => { tlFilter = k; $$('.tab', chips).forEach(x => x.classList.toggle('on', x === b)); renderTimeline(); };
      chips.appendChild(b);
    });
    renderTimeline();
  }
  function renderTimeline() {
    const yr = PL().year || '';
    const items = [...T.filter(vis).map(x => ({ ...x, war: false }))];
    steps().forEach((st, n) => items.push({ d: st.date + (yr ? ' ' + yr : ''), html: `<b>${esc(st.title)}.</b> ${esc(st.text)}`, tag: st.tag, war: true, y: (st.y || (+yr || 1900) + 0.5) + n / 1000 }));
    items.sort((a, b) => (a.y || 0) - (b.y || 0));
    const show = items.filter(x => tlFilter === 'all' || (tlFilter === 'war' ? x.war : (!x.war && x.tag === tlFilter)));
    $('#tl').innerHTML = show.map(x => `<div class="tl-item ${x.tag || ''} ${x.war ? 'war' : ''}"><div class="d">${esc(x.d)}</div><div class="t">${x.html} ${x.war ? '' : tagHtml(x.tag)}</div></div>`).join('');
  }

  /* ---------------- report: images, toc, nav ---------------- */
  function initReport() {
    const reps = $$('article.report'); if (!reps.length) return;
    reps.forEach(rep => {
      const repImgs = $$('img[data-src]', rep);
      const items = repImgs.map(im => docItem(im.dataset.src));
      repImgs.forEach((im, n) => im.addEventListener('click', () => LB.open(items, n)));
    });
    // scrollspy for toc and top nav
    const navs = $$('.nav a'), secs = navs.map(a => document.getElementById(a.hash.slice(1))).filter(Boolean);
    const onScroll = () => {
      const links = $$('.report-layout:not([hidden]) .toc a'), heads = links.map(a => document.getElementById(a.hash.slice(1))).filter(Boolean);
      const top = h => h.getBoundingClientRect().top;
      let k = -1; heads.forEach((h, n) => { if (top(h) <= 130) k = n; });
      links.forEach((a, n) => a.classList.toggle('on', n === k));
      let j = -1; secs.forEach((h, n) => { if (top(h) <= 130) j = n; });
      navs.forEach((a, n) => a.classList.toggle('on', n === j));
    };
    document.addEventListener('scroll', onScroll, { passive: true }); onScroll();
    $$('.toc a').forEach(a => a.addEventListener('click', () => { const d = a.closest('details'); if (d && window.innerWidth < 1000) d.open = false; }));
    $$('[data-goto-view]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); $('#mapsec').scrollIntoView({ behavior: 'smooth' }); setView(a.dataset.gotoView, true); }));
    $$('[data-goto-place]').forEach(a => a.addEventListener('click', e => {
      e.preventDefault(); const p = S.places.find(x => x.key === a.dataset.gotoPlace); if (!p) return;
      $('#mapsec').scrollIntoView({ behavior: 'smooth' });
      if (!p.views.includes(view)) setView(p.views[0], false);
      setTimeout(() => { map.flyTo([p.lat, p.lon], 9, { duration: 0.8 }); setTimeout(() => markers[p.key].openPopup(), 900); }, 350);
    }));
  }

  /* ---------------- search ---------------- */
  function initSearch() {
    const inp = $('#q'), bar = $('#search-bar'); if (!inp || !$('article.report')) return;
    let hits = [], k = 0, tm, scope = null;
    const clear = () => { $$('mark.hit').forEach(m => { const p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize(); }); hits = []; };
    const run = () => {
      clear(); const q = inp.value.trim(); galQuery = q.length >= 2 ? q : ''; renderGallery();
      if (q.length < 2) { bar.classList.remove('on'); return; }
      scope = $('.report-layout:not([hidden]) article.report');
      const ql = q.toLowerCase(), walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT), nodes = [];
      while (walker.nextNode()) if (walker.currentNode.nodeValue.toLowerCase().includes(ql)) nodes.push(walker.currentNode);
      nodes.forEach(n => {
        let s = n.nodeValue, low = s.toLowerCase(), pos = 0, idx; const frag = document.createDocumentFragment();
        while ((idx = low.indexOf(ql, pos)) >= 0 && hits.length < 800) {
          frag.appendChild(document.createTextNode(s.slice(pos, idx)));
          const m = document.createElement('mark'); m.className = 'hit'; m.textContent = s.slice(idx, idx + q.length); frag.appendChild(m); hits.push(m); pos = idx + q.length;
        }
        frag.appendChild(document.createTextNode(s.slice(pos))); n.parentNode.replaceChild(frag, n);
      });
      k = 0; bar.classList.add('on'); go(0);
    };
    const go = d => {
      $('#hit-count').textContent = hits.length ? t('hits', { k: k + 1, n: hits.length }) : t('noHits');
      hits.forEach(h => h.classList.remove('cur')); if (!hits.length) return;
      k = (k + d + hits.length) % hits.length; hits[k].classList.add('cur');
      $('#hit-count').textContent = t('hits', { k: k + 1, n: hits.length });
      const det = hits[k].closest('details'); if (det) det.open = true;
      hits[k].scrollIntoView({ behavior: 'smooth', block: 'center' });
    };
    inp.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(run, 300); });
    rerunSearch = run;
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); hits.length ? go(e.shiftKey ? -1 : 1) : run(); } if (e.key === 'Escape') { inp.value = ''; run(); inp.blur(); } });
    $('#hit-prev').onclick = () => go(-1); $('#hit-next').onclick = () => go(1);
    $('#hit-close').onclick = () => { inp.value = ''; run(); };
    inp.addEventListener('focus', () => $('.search').classList.add('open'));
    inp.addEventListener('blur', () => setTimeout(() => $('.search').classList.remove('open'), 150));
  }

  /* ---------------- family tree links ---------------- */
  function drawTreeLinks() {
    const box = $('.tree-box'); if (!box) return; const svg = $('svg.links', box); if (!svg) return;
    const r0 = box.getBoundingClientRect(), d = {};
    $$('[data-parent]', box).forEach(ch => {
      ch.dataset.parent.split(' ').forEach(pid => {
        const p = document.getElementById(pid); if (!p) return;
        const a = p.getBoundingClientRect(), b = ch.getBoundingClientRect(), c = LC[p.dataset.line] || '#c9bfae';
        const x1 = a.left + a.width / 2 - r0.left, y1 = a.bottom - r0.top, x2 = b.left + b.width / 2 - r0.left, y2 = b.top - r0.top, ym = (y1 + y2) / 2;
        d[c] = (d[c] || '') + `M${x1},${y1} C${x1},${ym} ${x2},${ym} ${x2},${y2} `;
      });
    });
    svg.setAttribute('viewBox', `0 0 ${r0.width} ${r0.height}`); svg.setAttribute('width', r0.width); svg.setAttribute('height', r0.height);
    svg.innerHTML = Object.entries(d).map(([c, p]) => `<path d="${p}" fill="none" stroke="${c}" stroke-width="2"${c === '#c9bfae' ? '' : ' stroke-opacity=".55"'}/>`).join('');
  }

  /* ---------------- versions: list, open old snapshot, what changed ---------------- */
  function initVersions() {
    const vm = $('#vm');
    if (!vm) return;
    const body = $('.vm-body', vm), head = $('.vm-title', vm), back = $('.vm-back', vm);
    const LOC = U.locale || 'ru-RU';
    const day = iso => new Date(iso).toLocaleDateString(LOC, { day: 'numeric', month: 'long', year: 'numeric' });
    const when = iso => new Date(iso).toLocaleString(LOC, { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    const par = n => pl(n, U.parForms || ['абзац', 'абзаца', 'абзацев']);
    const title = v => typeof v.title === 'object' ? (v.title[U.lang] || Object.values(v.title)[0]) : v.title;
    const cache = {};
    let V = [];
    const secs = id => cache[id] || (cache[id] = fetch(`v/${id}/sections${U.secSuffix || ''}.json`).then(r => r.json()));

    fetch('versions.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).then(j => {
      if (!j || !j.versions.length) return;
      V = j.versions;
      const line = $('#ver-line');
      line.innerHTML = `${t('updated', { d: day(V[0].date) })} · <a href="#versions">${t('versionsN', { n: V.length })}</a>`;
      line.hidden = false; $('.ver-foot').hidden = false;
      $$('a[href="#versions"]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); history.replaceState(null, '', '#versions'); list(); }));
      if (location.hash === '#versions') list();
      window.addEventListener('hashchange', () => { if (location.hash === '#versions') list(); });
    }).catch(() => {});

    function show() { vm.classList.add('on'); document.body.style.overflow = 'hidden'; }
    function close() {
      vm.classList.remove('on'); document.body.style.overflow = '';
      if (location.hash === '#versions') history.replaceState(null, '', location.pathname);
    }
    $('.vm-close', vm).addEventListener('click', close);
    vm.addEventListener('click', e => { if (e.target === vm) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && vm.classList.contains('on')) close(); });
    back.addEventListener('click', list);

    function summary(ch) {
      if (!ch) return t('firstVersion');
      if (!ch.length) return t('lookOnly');
      return ch.map(c => {
        const n = c.kind === 'added' ? `${t('newSection')}, ${c.plus} ${par(c.plus)}` : c.kind === 'removed' ? t('sectionGone')
          : [c.plus && `+${c.plus}`, c.minus && `−${c.minus}`].filter(Boolean).join(' / ') + ' ' + par(Math.max(c.plus, c.minus));
        return `<span class="vch ${c.kind}">«${esc(c.title)}» <small>${n}</small></span>`;
      }).join(' ');
    }
    function list() {
      head.textContent = t('versions'); back.hidden = true;
      body.innerHTML = `<p class="vm-note">${t('versionsNote')}</p>` +
        V.map((v, i) => `<div class="vi">
          <div class="vi-h"><b>${when(v.date)}</b>${i === 0 ? `<span class="tag ok">${t('current')}</span>` : ''}<code>${v.id}</code></div>
          <p class="vi-t">${esc(title(v))}</p>
          <div class="vi-c">${summary(v.changes)}</div>
          <div class="vi-a">${v.changes && v.changes.length ? `<button class="btn" data-diff="${i}">${t('whatChanged')}</button>` : ''}${i > 0
            ? `<a class="btn" href="v/${v.id}/${PAGE}">${t('openVersion')}</a><button class="btn" data-cmp="${i}">${t('compare')}</button>` : ''}</div>
        </div>`).join('');
      $$('[data-diff]', body).forEach(b => b.addEventListener('click', () => diff(+b.dataset.diff + 1, +b.dataset.diff)));
      $$('[data-cmp]', body).forEach(b => b.addEventListener('click', () => diff(+b.dataset.cmp, 0)));
      show(); body.scrollTop = 0;
    }

    function lcs(a, b, eq) {
      const n = a.length, m = b.length, L = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
      for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = eq(a[i], b[j]) ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
      const ops = []; let i = 0, j = 0;
      while (i < n && j < m) {
        if (eq(a[i], b[j])) { ops.push(['=', a[i], b[j]]); i++; j++; } else if (L[i + 1][j] >= L[i][j + 1]) ops.push(['-', a[i++]]); else ops.push(['+', b[j++]]);
      }
      while (i < n) ops.push(['-', a[i++]]);
      while (j < m) ops.push(['+', b[j++]]);
      return ops;
    }
    function words(a, b) {
      const ops = lcs(a.split(/(\s+)/), b.split(/(\s+)/), (x, y) => x === y);
      const same = ops.filter(o => o[0] === '=' && o[1].trim()).length, total = ops.filter(o => (o[1] || '').trim()).length;
      if (same / Math.max(total, 1) < 0.35) return null;
      return ops.map(([k, t]) => k === '=' ? esc(t) : k === '-' ? `<del>${esc(t)}</del>` : `<ins>${esc(t)}</ins>`).join('');
    }
    function blocks(a, b) {
      const ops = lcs(a, b, (x, y) => x === y), out = [];
      let skip = 0;
      const flush = () => { if (skip) out.push(`<p class="d-skip">${t('unchanged', { n: skip, par: par(skip) })}</p>`); skip = 0; };
      for (let k = 0; k < ops.length;) {
        if (ops[k][0] === '=') { skip++; k++; continue; }
        flush();
        const del = [], ins = [];
        while (k < ops.length && ops[k][0] !== '=') (ops[k][0] === '-' ? del : ins).push(ops[k++][1]);
        while (del.length || ins.length) {
          const w = del.length && ins.length ? words(del[0], ins[0]) : null;
          if (w) { out.push(`<p class="d-mod">${w}</p>`); del.shift(); ins.shift(); }
          else if (del.length) out.push(`<p class="d-del">${esc(del.shift())}</p>`);
          else out.push(`<p class="d-ins">${esc(ins.shift())}</p>`);
        }
      }
      flush();
      return out.join('');
    }
    function diff(oi, ni) {
      const o = V[oi], n = V[ni];
      head.textContent = t('whatChanged'); back.hidden = false;
      body.innerHTML = `<p class="vm-note">${t('loading')}</p>`; show();
      Promise.all([secs(o.id), secs(n.id)]).then(([A, B]) => {
        const om = new Map(A.map(s => [s.title, s.blocks])), nt = new Set(B.map(s => s.title));
        let h = '';
        B.forEach(s => {
          if (!om.has(s.title)) { h += `<h3>${esc(s.title)} <span class="vch added">${t('newSection')}</span></h3>` + s.blocks.map(t => `<p class="d-ins">${esc(t)}</p>`).join(''); return; }
          const a = om.get(s.title);
          if (a.join('\n') !== s.blocks.join('\n')) h += `<h3>${esc(s.title)}</h3>` + blocks(a, s.blocks);
        });
        A.forEach(s => { if (!nt.has(s.title)) h += `<h3>${esc(s.title)} <span class="vch removed">${t('sectionGone')}</span></h3>` + s.blocks.map(t => `<p class="d-del">${esc(t)}</p>`).join(''); });
        body.innerHTML = `<p class="vm-note">${t('was')} <b>${when(o.date)}</b> «${esc(title(o))}» → ${t('became')} <b>${when(n.date)}</b>${ni === 0 ? t('currentParen') : ` «${esc(title(n))}»`}.
            <span class="d-legend"><ins>${t('added')}</ins> <del>${t('removed')}</del></span></p>
          <div class="d-acts">${oi > 0 ? `<a class="btn" href="v/${o.id}/${PAGE}">${t('openWas')}</a>` : ''}</div>` +
          (h || `<p class="vm-note">${t('sameText')}</p>`);
        body.scrollTop = 0;
      }).catch(() => { body.innerHTML = `<p class="vm-note">${t('loadFail')}</p>`; });
    }
  }

  /* ---------------- family line switch and language ---------------- */
  const lineMem = {};   // per line: where the reader was on the page and in the path by dates
  function setLine(l, keepView) {
    if (!LINES || !LC[l]) return;
    // the section the reader is in: each line returns to its own place; the first visit starts at the top of the section
    // where the switch bar sits once stuck under the top bar (above that it is still in the page flow)
    const lb = $('#linebar'), tb = $('.topbar'), edge = (tb ? tb.offsetHeight : 0) + (lb ? lb.offsetHeight : 0) + 4;
    const sec = keepView ? null : ['mapsec', 'docs', 'chrono', 'report'].map(id => document.getElementById(id))
      .filter(x => x && x.getBoundingClientRect().top < edge).pop();
    // the place is kept as section + offset inside it: blocks above (the step card, the gallery) differ in height between lines
    if (!keepView && l !== line) lineMem[line] = { sec: sec && sec.id, off: sec ? -sec.getBoundingClientRect().top : 0, step: cur };
    const back = keepView ? null : lineMem[l];
    line = l; try { localStorage.setItem('kinship-line', l); } catch (e) { }
    const st = document.documentElement.style;
    st.setProperty('--accent', LC[l]); st.setProperty('--accent-soft', LC[l] + '1c');
    $$('#linebar [data-line]').forEach(b => { b.classList.toggle('on', b.dataset.line === l); b.setAttribute('aria-selected', b.dataset.line === l); });
    $$('.line-card').forEach(c => c.classList.toggle('on', c.dataset.line === l));
    $$('.report-layout[data-line]').forEach(r => r.hidden = r.dataset.line !== l);
    $$('#map-tabs .tab').forEach(b => b.hidden = !vis(S.views[b.dataset.view]));
    if (timer) stopPlay();
    renderSteps(); initGallery(); initTimeline();
    $$('#steps, #gal-chips, #tl-chips, #map-tabs').forEach(x => x.scrollLeft = 0);
    if (map) {
      map.closePopup(); $$('.pin.pulse').forEach(e => e.classList.remove('pulse'));
      if (!keepView && steps().length) goStep(back ? Math.min(back.step, steps().length - 1) : 0, true);   // the line's own step, or its beginning
      else if (!keepView && !vis(S.views[view])) setView(viewKeys()[0], true);
      else drawView(false);
    }
    if (rerunSearch && $('#q').value) rerunSearch();
    if (sec && back && back.sec) window.scrollTo({ top: document.getElementById(back.sec).getBoundingClientRect().top + scrollY + back.off, behavior: 'instant' });
    else if (sec && sec.getBoundingClientRect().top < edge - 8) sec.scrollIntoView({ behavior: 'instant', block: 'start' });
  }
  function initLines() {
    $$('a.lang').forEach(a => a.addEventListener('click', () => {
      try { localStorage.setItem('kinship-lang', a.dataset.lang); } catch (e) { }
      a.href = a.getAttribute('href').split('#')[0] + location.hash;
    }));
    if (!LINES) return;
    $$('#linebar [data-line]').forEach(b => b.addEventListener('click', () => setLine(b.dataset.line)));
    $$('[data-set-line]').forEach(a => a.addEventListener('click', () => setLine(a.dataset.setLine)));
    setLine(line, true);
  }

  document.addEventListener('DOMContentLoaded', () => {
    initMap(); initPlayer(); initGallery(); initTimeline(); initReport(); initSearch(); drawTreeLinks(); initVersions(); initLines();
    $$('img[data-lb]').forEach(im => im.addEventListener('click', () => LB.open([docItem(im.dataset.lb)])));
    window.addEventListener('resize', drawTreeLinks);
    $$('.person[data-place]').forEach(c => c.addEventListener('click', () => {
      if (c.dataset.line) setLine(c.dataset.line);
      const a = document.createElement('a'); a.dataset.gotoPlace = c.dataset.place; document.body.appendChild(a);
      initReportLink(a); a.click(); a.remove();
    }));
  });
  function initReportLink(a) {
    a.addEventListener('click', e => {
      e.preventDefault(); const p = S.places.find(x => x.key === a.dataset.gotoPlace); if (!p || !map) return;
      $('#mapsec').scrollIntoView({ behavior: 'smooth' });
      if (!p.views.includes(view)) setView(p.views[0], false);
      setTimeout(() => { map.flyTo([p.lat, p.lon], 9, { duration: 0.8 }); setTimeout(() => markers[p.key].openPopup(), 900); }, 350);
    });
  }
})();
