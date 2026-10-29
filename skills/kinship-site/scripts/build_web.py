"""Builds the live HTML version of a kinship report into <case>/web/.

Usage: python3 -I build_web.py <case dir> [natural-earth geojson dir]
Text comes from pdf-source/report.html (same source as the PDF), page settings from pdf-source/web/site.json,
map data from pdf-source/web/story.json, coordinates from pdf-source/maps/geocode.json.
The Natural Earth dir defaults to site.json "naturalEarth", then ~/.cache/kinship-site/naturalearth.
Images are converted with macOS `sips`.

Optional, for one site over several family lines and languages (see references/config.md):
  site.json "langs": ["ka", "ru"]  — the first language is index.html, the others <lang>.html;
                                     any text in site.json / story.json may be {"ka": "…", "ru": "…"}
  site.json "lines": [{key, report, pdf, …}] — each line has its own report; a switch on the page picks the line.
"""
import copy, html, json, math, os, re, shutil, subprocess, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASE = os.path.abspath(sys.argv[1])
SRC = os.path.join(CASE, 'pdf-source')
HERE = os.path.join(SRC, 'web')
OUT = os.path.join(CASE, 'web')
IMG, THUMB = os.path.join(OUT, 'img'), os.path.join(OUT, 'img', 'thumb')

CFG = json.load(open(os.path.join(HERE, 'site.json'), encoding='utf-8'))
STORY = json.load(open(os.path.join(HERE, 'story.json'), encoding='utf-8'))
UI = json.load(open(os.path.join(SKILL, 'assets', 'ui.json'), encoding='utf-8'))
LANGS = CFG.get('langs') or [None]
MULTI = bool(CFG.get('lines'))
gc_path = os.path.join(SRC, 'maps', 'geocode.json')
geocode = json.load(open(gc_path, encoding='utf-8')) if os.path.exists(gc_path) else {}
GEO = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else CFG.get('naturalEarth', '~/.cache/kinship-site/naturalearth'))
if not os.path.isabs(GEO):
    GEO = os.path.join(CASE, GEO)
for d in (IMG, THUMB, os.path.join(OUT, 'assets', 'vendor'), os.path.join(OUT, 'data')):
    os.makedirs(d, exist_ok=True)


def loc(x, lang):
    """Picks one language out of {"ka": …, "ru": …} values anywhere in a config tree."""
    if lang is None:
        return x
    if isinstance(x, dict):
        if x and set(x) <= set(LANGS):
            return loc(x.get(lang, x.get(LANGS[0])), lang)
        return {k: loc(v, lang) for k, v in x.items()}
    if isinstance(x, list):
        return [loc(v, lang) for v in x]
    return x


# ---------------------------------------------------------------- images
done = {}


def dims(path):
    out = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', path], capture_output=True, text=True).stdout
    w = re.search(r'pixelWidth: (\d+)', out); h = re.search(r'pixelHeight: (\d+)', out)
    return (int(w.group(1)), int(h.group(1))) if w and h else (0, 0)


def sips_jpeg(src, dst, maxdim, q):
    w, h = dims(src)
    args = ['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', str(q)]
    if max(w, h) > maxdim:
        args += ['-Z', str(maxdim)]
    subprocess.run(args + [src, '--out', dst], capture_output=True, check=True)


def web_img(src_rel, base=SRC, prefix=''):
    """src_rel is relative to base (the folder of the report that uses it). Returns (web src, thumb, original link).
    prefix keeps same-named images of different family lines apart."""
    path = os.path.normpath(os.path.join(base, src_rel))
    if path in done:
        return done[path]
    if not os.path.exists(path):
        print('MISSING image', src_rel)
        done[path] = (src_rel, src_rel, '')
        return done[path]
    flat = prefix + re.sub(r'^(\.\./)+', '', src_rel).replace('/', '__')
    stem, ext = os.path.splitext(flat)
    orig = os.path.relpath(path, OUT)
    if ext.lower() == '.svg':
        shutil.copy2(path, os.path.join(IMG, flat))
        done[path] = ('img/' + flat, 'img/' + flat, orig)
    else:
        big = th = stem + '.jpg'
        if not os.path.exists(os.path.join(IMG, big)) or os.path.getmtime(os.path.join(IMG, big)) < os.path.getmtime(path):
            sips_jpeg(path, os.path.join(IMG, big), 2200, 82)
            sips_jpeg(path, os.path.join(THUMB, th), 560, 70)
        done[path] = ('img/' + big, 'img/thumb/' + th, orig)
    return done[path]


# ---------------------------------------------------------------- report body
def parse_report(path, cfg, U, line=None):
    """One report.html → its text for the page, contents, figures for the gallery and chronology rows."""
    report = open(path, encoding='utf-8').read()
    base = os.path.dirname(path)
    key = line['key'] if line else ''
    prefix = key + '__' if key else ''
    body = re.search(r'<body>(.*)</body>', report, re.S).group(1)
    R = {'line': line, 'h1': re.findall(r'<h1>(.*?)</h1>', body, re.S)[:1],
         'legend': re.search(r'<p class="legend"[^>]*>(.*?)</p>', body, re.S),
         'lead': re.search(r'<div class="lead">\s*<ul>(.*?)</ul>\s*</div>', body, re.S),
         'sub': re.findall(r'<p class="sub">(.*?)</p>', body, re.S)}
    head = body[:body.index('<div class="lead">')] if R['lead'] else ''
    rest = body[body.index('</div>', body.index('<div class="lead">')) + 6:] if R['lead'] else body
    if line:   # a note in the header (e.g. «machine translation») would be lost with the header
        rest = ''.join(re.findall(r'<p class="small">.*?</p>', head, re.S)) + rest

    toc, slug = [], [0]

    def h2(m):
        slug[0] += 1
        title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        sid = f'{key}-s{slug[0]}' if key else f's{slug[0]}'
        toc.append((sid, title))
        return f'<h2 id="{sid}">{m.group(2)}</h2>'

    rest = re.sub(r'<h2([^>]*)>(.*?)</h2>', h2, rest, flags=re.S)
    rest = re.sub(r'(<table>.*?</table>)', r'<div class="tscroll">\1</div>', rest, flags=re.S)

    # gallery from figures, grouped by the section they are in
    gallery = []
    section_at = [(m.start(), re.sub(r'<[^>]+>', '', m.group(1)).strip()) for m in re.finditer(r'<h2 id="[\w-]+">(.*?)</h2>', rest, re.S)]

    def section_of(pos):
        name = ''
        for p, t in section_at:
            if p <= pos:
                name = t
        name = re.sub(r'^Приложение\.\s*', '', name)
        return name[:1].upper() + name[1:]

    mapview = cfg.get('mapFigures', {})   # static map file in report.html → interactive view to open

    def figure(m):
        fig = m.group(0)
        cap = re.search(r'<figcaption>(.*?)</figcaption>', fig, re.S)
        cap_html = cap.group(1).strip() if cap else ''
        cap_text = html.unescape(re.sub(r'<[^>]+>', '', cap_html)).strip()
        grp = section_of(m.start())

        def img(mm):
            src = mm.group(1)
            w, th, orig = web_img(src, base, prefix)
            g = {'src': w, 'thumb': th, 'full': orig, 'cap': cap_html, 'text': cap_text,
                 'grp': U['grpMaps'] if src.startswith('maps/') else grp, 'inGallery': True}
            if key:
                g['line'] = key
            gallery.append(g)
            return f'<img src="{w}" data-src="{w}" loading="lazy"' + mm.group(2)

        fig = re.sub(r'<img src="([^"]+)"([^>]*>)', img, fig)
        for name, v in mapview.items():
            if name in fig:
                fig = fig.replace('</figcaption>', f'<br><a class="map-link" href="#mapsec" data-goto-view="{v}">{U["openOnMap"]}</a></figcaption>')
        return fig

    rest = re.sub(r'<figure[^>]*>.*?</figure>', figure, rest, flags=re.S)
    # images outside figures (fragments)
    rest = re.sub(r'<img src="(\.\./[^"]+)"', lambda mm: f'<img src="{web_img(mm.group(1), base, prefix)[0]}" data-src="{web_img(mm.group(1), base, prefix)[0]}"', rest)

    # timeline: the chronology table of the report
    tcfg = cfg.get('timeline', {})
    timeline = []
    chrono = re.search(r'<h2 id="[\w-]+">' + re.escape(tcfg.get('section', 'Хронология')) + r'</h2>\s*<div class="tscroll"><table>.*?<tbody>(.*?)</tbody>', rest, re.S)
    for row in re.findall(r'<tr>(.*?)</tr>', chrono.group(1) if chrono else '', re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
        if len(tds) < 3:
            continue
        d = html.unescape(re.sub(r'<[^>]+>', '', tds[0])).strip()
        tag = re.search(r'class="tag (\w+)"', tds[2])
        it = {'d': d, 'html': tds[1].strip(), 'tag': tag.group(1) if tag else '', 'y': year_of(d, tcfg)}
        if key:
            it['line'] = key
        timeline.append(it)
    R.update(rest=rest, toc=toc, gallery=gallery, timeline=timeline)
    return R


MONTHS = ['янв', 'февр', 'мар', 'апр', 'мая', 'май', 'июн', 'июл', 'авг', 'сент', 'окт', 'нояб', 'дек']


def year_of(d, tcfg):
    yrs = [int(x) for x in re.findall(r'(1[6-9]\d\d|20\d\d)', d)]
    y = yrs[0] if yrs else tcfg.get('defaultYear', 1900)
    if d.startswith('до '):
        y -= 0.1
    for phrase, yy in tcfg.get('special', {}).items():   # e.g. {"перед войной": 1940.5}
        if phrase in d:
            y = yy
    mon = re.search('(' + '|'.join(MONTHS) + ')', d)
    if mon:
        y += MONTHS.index(mon.group(1)) / 13
    return round(y, 3)


# ---------------------------------------------------------------- basemap (Natural Earth, clipped to the area of the case)
def build_geo(bm):
    BB = tuple(bm['bbox'])                       # lon0, lat0, lon1, lat1
    RIVER_NAMED = set(bm.get('riversNamed', []))
    LAKES = bm.get('lakes', ['Caspian'])         # only real lakes of the period: reservoirs did not exist yet

    def inside(x, y, pad=0.0):
        return BB[0] - pad <= x <= BB[2] + pad and BB[1] - pad <= y <= BB[3] + pad

    def simplify(pts, tol):
        out = []
        for x, y in pts:
            x, y = round(x, 3), round(y, 3)
            if not out or math.hypot(x - out[-1][0], y - out[-1][1]) >= tol:
                out.append([x, y])
        return out

    def load(name):
        fn = os.path.join(GEO, name + '.geojson')
        if not os.path.exists(fn):
            sys.exit(f'{fn} not found: run fetch_naturalearth.sh')
        return json.load(open(fn, encoding='utf-8'))['features']

    water = []
    for f in load('ne_10m_ocean') + [f for f in load('ne_10m_lakes') if any(n in str(f['properties'].get('name')) for n in LAKES)]:
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys:
            rings = []
            for ring in poly:
                if not any(inside(x, y, 0.5) for x, y in ring[::3]):
                    continue
                cl = [[min(max(x, BB[0] - 1), BB[2] + 1), min(max(y, BB[1] - 1), BB[3] + 1)] for x, y in ring]
                s = simplify(cl, bm.get('coastTolerance', 0.01))   # coarser for a large area keeps geo.js small
                if len(s) > 3:
                    rings.append(s + [s[0]])
            if rings:
                water.append({'type': 'Feature', 'properties': {}, 'geometry': {'type': 'Polygon', 'coordinates': rings}})
    named, other = [], []
    for f in load('ne_10m_rivers_lake_centerlines') + load('ne_10m_rivers_europe'):
        g = f['geometry']
        if not g:
            continue
        lines = g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]
        keep = []
        for l in lines:
            seg = [p for p in l if inside(p[0], p[1], 0.3)]
            s = simplify(seg, bm.get('riverTolerance', 0.006))
            if len(s) > 1:
                keep.append(s)
        if keep:
            feat = {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiLineString', 'coordinates': keep}}
            (named if f['properties'].get('name') in RIVER_NAMED else other).append(feat)
    return {'water': {'type': 'FeatureCollection', 'features': water},
            'riversNamed': {'type': 'FeatureCollection', 'features': named},
            'riversOther': {'type': 'FeatureCollection', 'features': other},
            'riverLabels': loc(bm.get('riverLabels', []), LANGS[0])}   # [name, lat, lon]


geo = build_geo(CFG.get('basemap', {}))
open(os.path.join(OUT, 'data', 'geo.js'), 'w', encoding='utf-8').write('window.GEO=' + json.dumps(geo, ensure_ascii=False, separators=(',', ':')) + ';')
for f in ('app.css', 'app.js'):
    shutil.copy2(os.path.join(SKILL, 'assets', f), os.path.join(OUT, 'assets', f))
for f in ('leaflet.css', 'leaflet.js'):
    shutil.copy2(os.path.join(SKILL, 'assets', 'vendor', f), os.path.join(OUT, 'assets', 'vendor', f))

# CI stages the site from the repo, so the case keeps its own copy of stage_public.py; keep it in sync with the skill
vend = os.path.join(HERE, 'stage_public.py')
mine = open(os.path.join(SKILL, 'scripts', 'stage_public.py'), encoding='utf-8').read()
if not os.path.exists(vend) or open(vend, encoding='utf-8').read() != mine:
    open(vend, 'w', encoding='utf-8').write(mine)
    print('updated', os.path.relpath(vend, CASE))

esc = html.escape
OVR = CFG.get('placeOverrides', {})   # key → {"from": other key, "dlat": .., "dlon": ..} or {"lat": .., "lon": ..}


def ll(key):
    o = OVR.get(key)
    if o and 'lat' in o:
        return o['lat'], o['lon']
    p = geocode[o['from'] if o else key][0]
    return p['lat'] + (o or {}).get('dlat', 0), p['lon'] + (o or {}).get('dlon', 0)


missing = [p['key'] for p in STORY['places'] if p['key'] not in geocode and p['key'] not in OVR]
if missing:
    sys.exit(f'no coordinates for {missing}: run geocode.py or add placeOverrides')


def page_name(lang):
    return 'index.html' if lang == LANGS[0] else f'{lang}.html'


def build(lang):
    cfg, story = loc(CFG, lang), loc(copy.deepcopy(STORY), lang)
    U = {**UI['ru'], **UI.get(lang or 'ru', {}), **cfg.get('ui', {})}
    first = lang == LANGS[0]
    suffix = '' if first else f'.{lang}'
    U['secSuffix'] = suffix
    U['lang'] = lang or 'ru'
    lines = cfg.get('lines') or []
    if lines:
        reports = [parse_report(os.path.normpath(os.path.join(CASE, ln['report'])), cfg, U, ln) for ln in lines]
    else:
        reports = [parse_report(os.path.join(SRC, 'report.html'), cfg, U)]
    gallery = [g for r in reports for g in r['gallery']]
    timeline = [t for r in reports for t in r['timeline']]
    for c in story.pop('chrono', []):   # chronology rows kept in story.json: {d, text, tag, y, line}
        it = {'d': c['d'], 'html': c['text'], 'tag': c.get('tag', ''), 'y': c.get('y') or year_of(c['d'], cfg.get('timeline', {}))}
        if c.get('line'):
            it['line'] = c['line']
        timeline.append(it)

    # ------------------------------------------------------------ story data
    gal_by_src = {g['src']: g for g in gallery}
    player = story.get('player', {})
    for p in story['places']:
        p['lat'], p['lon'] = [round(v, 4) for v in ll(p['key'])]
        for e in p.get('events', []):
            if e.get('img'):
                w, th, orig = web_img(e['img'])
                if w not in gal_by_src:
                    gal_by_src[w] = {'src': w, 'thumb': th, 'full': orig, 'cap': html.escape(e['text']), 'text': e['text'], 'grp': p['name'], 'inGallery': False}
                    if p.get('line'):
                        gal_by_src[w]['line'] = p['line']
                    gallery.append(gal_by_src[w])
                e['img'] = w
    for st in story.get('steps', []):
        if st.get('img'):
            w, th, orig = web_img(st['img'])
            if w not in gal_by_src:
                grp = (player.get('byLine', {}).get(st.get('line'), {}) or player).get('group') or player.get('group', U['grpSteps'])
                gal_by_src[w] = {'src': w, 'thumb': th, 'full': orig, 'cap': html.escape(st['src'] + ': ' + st['quote']), 'text': st['quote'],
                                 'grp': grp, 'inGallery': False}
                if st.get('line'):
                    gal_by_src[w]['line'] = st['line']
                gallery.append(gal_by_src[w])
            st['img'] = w
    if lang and not first:
        story['riverLabels'] = cfg.get('basemap', {}).get('riverLabels', [])

    pdfs = {}   # line key ('' for a one-report case) → link
    if lines:
        os.makedirs(os.path.join(OUT, 'pdf'), exist_ok=True)
        for ln in lines:
            if ln.get('pdf'):
                src = os.path.normpath(os.path.join(CASE, ln['pdf']))
                dst = os.path.join(OUT, 'pdf', ln['publicPdf'])
                if not os.path.exists(dst) or open(dst, 'rb').read() != open(src, 'rb').read():
                    shutil.copy2(src, dst)
                pdfs[ln['key']] = 'pdf/' + ln['publicPdf']
    else:
        pdfs[''] = os.path.relpath(os.path.join(CASE, cfg['pdf']), OUT)

    data = ('window.STORY=' + json.dumps(story, ensure_ascii=False, separators=(',', ':')) + ';\n'
            'window.GALLERY=' + json.dumps(gallery, ensure_ascii=False, separators=(',', ':')) + ';\n'
            'window.TIMELINE=' + json.dumps(timeline, ensure_ascii=False, separators=(',', ':')) + ';\n'
            'window.UI=' + json.dumps(U, ensure_ascii=False, separators=(',', ':')) + ';\n')
    if lines:
        data += 'window.LINES=' + json.dumps([{k: ln.get(k) for k in ('key', 'label', 'surname', 'color')} for ln in lines], ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(os.path.join(OUT, 'data', f'story{suffix}.js'), 'w', encoding='utf-8').write(data)

    # ------------------------------------------------------------ page
    def facts_of(r, limit=None):
        out = ''
        lis = re.findall(r'<li>(.*?)</li>', r['lead'].group(1) if r['lead'] else '', re.S)
        for li in (lis if limit is None else [lis[i] for i in limit if i < len(lis)] if isinstance(limit, list) else lis[:limit]):
            m = re.match(r'\s*<b>(.*?)</b>\s*(.*)', li, re.S)
            t, rest_li = (m.group(1), m.group(2)) if m else ('', li)
            rest_li = rest_li.strip()
            if rest_li.startswith(','):
                rest_li = rest_li.lstrip(', ')
                rest_li = rest_li[:1].upper() + rest_li[1:]
            out += f'<div class="fact card"><b>{t}</b><p>{rest_li}</p></div>' if limit is None else f'<li><b>{t}</b> {rest_li}</li>'
        return out

    R0 = reports[0]
    legend_row = ' '.join(re.findall(r'<span class="tag [^"]+">[^<]+</span> — [^<]+', R0['legend'].group(1) if R0['legend'] else ''))
    n_docs = sum(1 for g in gallery if g['inGallery'] and g['grp'] != U['grpMaps'])
    n_places = sum(1 for p in story['places'] if p['kind'] != 'ref')

    hero_photo = ''
    hp = cfg.get('heroPhoto')
    if hp and os.path.exists(os.path.normpath(os.path.join(SRC, hp['src']))):
        hw = web_img(hp['src'])[0]
        hero_photo = (f'<figure class="hero-photo"><img src="{hw}" data-lb="{hw}" alt="{esc(hp.get("alt", ""))}">'
                      f'<figcaption>{hp.get("caption", "")}</figcaption></figure>')

    def person(p):
        if p.get('spacer'):
            return '<div class="person spacer" aria-hidden="true"></div>'
        attrs = f' id="{p["id"]}"'
        if p.get('parents'):
            attrs += f' data-parent="{" ".join(p["parents"])}"'
        if p.get('place'):
            attrs += f' data-place="{p["place"]}"'
        if p.get('line'):
            attrs += f' data-line="{p["line"]}" style="--lc:{line_color.get(p["line"], "")}"'
        tag = f'<span class="tag {p["tag"]}">{p["tagText"]}</span>' if p.get('tag') else ''
        return f'<div class="person card{" dashed" if p.get("dashed") else ""}"{attrs}><b>{p["name"]}</b><small>{p.get("sub", "")}</small>{tag}</div>'

    line_color = {ln['key']: ln['color'] for ln in lines}
    tree = cfg.get('tree', {})
    gens = []
    for g in tree.get('gens', []):
        people = g['people']
        if len(people) == 1:
            gens.append(f'  <div class="gen" data-label="{g.get("label", "")}">{person(people[0])}</div>')
        else:
            gens.append(f'  <div class="gen" data-label="{g.get("label", "")}">\n' + ''.join(f'    {person(p)}\n' for p in people) + '  </div>')
    TREE = '\n<div class="tree"><div class="tree-box"><svg class="links"></svg><div class="tree-inner">\n' + '\n'.join(gens) + '\n</div></div></div>'

    views = story['views']
    line_attr = lambda v: f' data-line="{v["line"]}"' if v.get('line') else ''
    tabs = ''.join(f'<button class="tab" data-view="{k}"{line_attr(v)}>{esc(v["title"])}</button>' for k, v in views.items())
    player_html = ''
    if story.get('steps'):
        player_html = f'''
    <aside class="player card" id="player">
      <h3>{esc(player.get('title', U['playerTitle']))}</h3>
      <div class="steps" id="steps"></div>
      <div class="step-card" id="step-card"></div>
      <div class="player-nav"><button class="btn" id="step-prev" aria-label="{U['back']}">←</button><button class="btn primary" id="step-next">{U['next']}</button><button class="btn" id="step-play">{U['play']}</button><span class="count" id="step-count"></span></div>
    </aside>'''

    # ------------------------------------------------------------ parts that exist only on sites with lines / languages
    extra_head = arrowheads = lang_switch = line_bar = ''
    if lang:
        if cfg.get('fonts'):
            extra_head += f'\n<link rel="stylesheet" href="{esc(cfg["fonts"])}">'
        if first and len(LANGS) > 1:   # come back to the language the reader chose last time
            others = json.dumps([l for l in LANGS[1:]])
            extra_head += ('\n<script>try{var l=localStorage.getItem("kinship-lang");if(' + others + '.indexOf(l)>=0)'
                           'location.replace(l+".html"+location.hash)}catch(e){}</script>')
        lang_switch = ''.join(f'<a class="lang" data-lang="{l}" href="{"./" if l == LANGS[0] else l + ".html"}" hreflang="{l}">{esc(CFG.get("langNames", {}).get(l, l))}</a>'
                              for l in LANGS if l != lang)
    if lines:
        arrowheads = ''.join(f'<marker id="arrowhead-{ln["key"]}" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{ln["color"]}"/></marker>' for ln in lines)
        line_bar = ('\n<div class="linebar" id="linebar"><div class="wrap"><div class="seg" role="tablist" aria-label="' + esc(U['lineAria']) + '">'
                    + ''.join(f'<button role="tab" data-line="{ln["key"]}" style="--lc:{ln["color"]}"><small>{ln["label"]}</small><b>{ln["surname"]}</b></button>' for ln in lines)
                    + '</div></div></div>')

    if lines:
        cards = ''
        for r in reports:
            ln = r['line']
            pdf = f'<a class="btn" href="{esc(pdfs[ln["key"]])}">PDF</a>' if ln['key'] in pdfs else ''
            cards += f'''
    <article class="line-card card" data-line="{ln['key']}" style="--lc:{ln['color']}">
      <p class="lc-k">{ln['label']}</p>
      <h2 class="lc-name">{ln['surname']}</h2>
      <p class="lc-who"><b>{r['h1'][0] if r['h1'] else ''}</b><small>{ln.get('place', '')}</small></p>
      <ul class="lc-facts">{facts_of(r, ln.get('facts', 3))}</ul>
      <div class="cta"><a class="btn primary" href="#mapsec" data-set-line="{ln['key']}">{U['lineMap']}</a><a class="btn" href="#report" data-set-line="{ln['key']}">{U['lineReport']}</a>{pdf}</div>
    </article>'''
        hero = f'''<section class="block hero" id="top"><div class="wrap">
  <p class="kicker">{cfg.get('kicker', '')}</p>
  <p class="updated" id="ver-line" hidden></p>
  <h1>{cfg['h1']}</h1>
  <p class="lede">{cfg.get('lede', '')}</p>
  <div class="lines">{cards}
  </div>
  <div class="legend-row">{legend_row}</div>
</div></section>'''
        report_html = ''.join(f'''
  <div class="report-layout" data-line="{r['line']['key']}">
    <aside class="toc"><details open><summary>{U['toc']}</summary><ol>{''.join(f'<li><a href="#{sid}">{esc(t)}</a></li>' for sid, t in r['toc'])}</ol></details></aside>
    <article class="report" id="report-body-{r['line']['key']}" data-title="{esc(re.sub(r'<[^>]+>', '', r['line']['surname']))}">{r['rest']}</article>
  </div>''' for r in reports)
    else:
        facts = facts_of(R0)
        sub = R0['sub']
        hero = f'''<section class="block hero" id="top"><div class="wrap">
  <p class="kicker">{cfg.get('kicker', '')}</p>
  <p class="updated" id="ver-line" hidden></p>
  <div class="hero-grid"><div>
  <h1>{cfg['h1']}</h1>
  <p class="lede">{sub[0] if sub else ''}</p>
  <div class="facts">{facts}</div>
  </div>{hero_photo}</div>
  <div class="legend-row">{legend_row}</div>
  <div class="cta"><a class="btn primary" href="#mapsec">{esc(cfg.get('ctaMap', U['ctaMap']))}</a><a class="btn" href="#docs">{U['docsN'].format(n=n_docs)}</a><a class="btn" href="{esc(pdfs[''])}">{U['pdf']}</a></div>
</div></section>'''
        toc_html = ''.join(f'<li><a href="#{sid}">{esc(t)}</a></li>' for sid, t in R0['toc'])
        report_html = f'''
  <div class="report-layout">
    <aside class="toc"><details open><summary>{U['toc']}</summary><ol>{toc_html}</ol></details></aside>
    <article class="report" id="report-body">{R0['rest']}</article>
  </div>'''

    page = f'''<!doctype html>
<html lang="{lang or 'ru'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#fbfaf7">
<title>{esc(cfg['title'])}</title>
<link rel="stylesheet" href="assets/vendor/leaflet.css"><link rel="stylesheet" href="assets/app.css">{extra_head}
</head><body{' class="has-lines"' if lines else ''}>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><marker id="arrowhead" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#7a2e1f"/></marker>{arrowheads}</defs></svg>
<header class="topbar"><div class="wrap">
  <a class="brand" href="#top">{esc(cfg['brand'])}<span class="long">{esc(cfg.get('brandLong', ''))}</span></a>
  <nav class="nav"><a href="#top">{U['navTop']}</a><a href="#tree">{U['navTree']}</a><a href="#mapsec">{U['navMap']}</a><a href="#docs">{U['navDocs']}</a><a href="#chrono">{U['navChrono']}</a><a href="#report">{U['navReport']}</a></nav>
  <label class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="q" type="search" placeholder="{U['search']}" aria-label="{U['searchAria']}"></label>{lang_switch}
</div></header>
<div class="search-bar" id="search-bar"><span id="hit-count"></span><button id="hit-prev" aria-label="{U['prevHit']}">↑</button><button id="hit-next" aria-label="{U['nextHit']}">↓</button><button id="hit-close" aria-label="{U['close']}">✕</button></div>

<main>
{hero}

<section class="block" id="tree"><div class="wrap">
  <p class="kicker">{U['treeKicker']}</p><h2 class="sec">{U['treeTitle']}</h2>
  <p class="lede">{tree.get('lede', U['treeLede'])}</p>
  {TREE}
</div></section>
{line_bar}
<section class="block" id="mapsec"><div class="wrap">
  <p class="kicker">{U['mapKicker'].format(n=n_places)}</p><h2 class="sec">{U['mapTitle']}</h2>
  <div class="map-tabs" id="map-tabs">
    {tabs}
  </div>
  <div class="chips" id="kind-chips" aria-label="{U['kindsAria']}"></div>
  <div class="map-layout">
    <div><div id="map" role="region" aria-label="{U['mapAria']}"></div>
      <p class="map-hint">{cfg.get('mapHint', U['mapHint'])}</p></div>{player_html}
  </div>
</div></section>

<section class="block" id="docs"><div class="wrap">
  <p class="kicker">{U['docsKicker']}</p><h2 class="sec">{U['docsTitle']}</h2>
  <p class="lede">{U['docsLede']}</p>
  <div class="chips" id="gal-chips"></div>
  <p class="map-hint" id="gal-count"></p>
  <div class="gal" id="gal"></div>
</div></section>

<section class="block" id="chrono"><div class="wrap">
  <p class="kicker">{U['chronoKicker']}</p><h2 class="sec">{U['chronoTitle']}</h2>
  <div class="chips" id="tl-chips"></div>
  <div class="tl" id="tl"></div>
</div></section>

<section class="block" id="report"><div class="wrap">
  <p class="kicker">{U['reportKicker']}</p><h2 class="sec">{U['reportTitle']}</h2>{report_html}
</div></section>
</main>
<footer><div class="wrap">{cfg.get('footer', U['footer'])} {U['footerMaps']}<span class="ver-foot" hidden> · <a href="#versions">{U['versions']}</a></span></div></footer>

<div class="vm" id="vm" role="dialog" aria-modal="true" aria-label="{U['versions']}"><div class="vm-box">
  <div class="vm-head"><button class="vm-back" hidden aria-label="{U['backToVersions']}">‹</button><b class="vm-title">{U['versions']}</b><button class="vm-close" aria-label="{U['close']}">✕</button></div>
  <div class="vm-body"></div>
</div></div>

<div class="lb" id="lb" role="dialog" aria-label="{U['lbAria']}">
  <div class="lb-top"><span class="count"></span><button class="lb-out" aria-label="{U['zoomOut']}">−</button><button class="lb-in" aria-label="{U['zoomIn']}">+</button><button class="lb-fit" aria-label="{U['fit']}">⤢</button><a class="lbtn lb-orig" target="_blank" rel="noopener">{U['original']}</a><button class="lb-close" aria-label="{U['close']}">✕</button></div>
  <div class="lb-stage"><img alt=""><button class="side prev" aria-label="{U['prevDoc']}">‹</button><button class="side next" aria-label="{U['nextDoc']}">›</button></div>
  <div class="lb-cap"></div>
</div>
<script src="assets/vendor/leaflet.js"></script><script src="data/geo.js"></script><script src="data/story{suffix}.js"></script><script src="assets/app.js"></script>
</body></html>'''
    open(os.path.join(OUT, page_name(lang)), 'w', encoding='utf-8').write(page)
    print(page_name(lang), len(page), 'bytes; images', len(done), '; gallery', len(gallery), '; timeline', len(timeline),
          '; toc', sum(len(r['toc']) for r in reports))


for lang in LANGS:
    build(lang)
for f in ('geo.js',) + tuple(f'story{"" if l == LANGS[0] else "." + l}.js' for l in LANGS):
    print(f, os.path.getsize(os.path.join(OUT, 'data', f)))
