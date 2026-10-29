"""Static SVG maps for kinship reports (stdlib only). Part of the kinship-site skill.

A case keeps its own pdf-source/maps/make_maps.py that lays out its maps:

    import os, sys
    sys.path.insert(0, os.path.expanduser('~/.claude/skills/kinship-site/scripts'))
    import maplib as M
    M.init(ne_dir, 'pdf-source/maps/geocode.json', 'pdf-source/maps', story='pdf-source/web/story.json')
    m = M.Map(lon0, lon1, lat0, lat1, 900); M.base(m, 2)
    m.place('key', 'Название', ['подпись'], kind='home'); m.save('map-family.svg', ['home'])

Kinds (colour + legend label) come from story.json "kinds", so the PDF maps and the site share one legend.
"""
import json, math, os

INK, MUTED, ACCENT = '#1d1d1f', '#5f6368', '#7a2e1f'
LAND, WATER, RIVER, GRID = '#f6f3ee', '#cfe0ea', '#6f9bbb', '#e4dfd5'
BLUE = '#2f5d8a'
# one colour per kind of mark, used for the badge behind the glyph; init() replaces labels/colours from story.json
KIND = {
    'home':     ('#7a2e1f', 'дом семьи'),
    'birth':    ('#b5651d', 'место рождения'),
    'missing':  ('#5b3a8c', 'пропал без вести'),
    'death':    ('#1d1d1f', 'погиб'),
    'pow':      ('#8a2f2f', 'плен'),
    'division': ('#2e6b3a', 'воинская часть'),
    'event':    ('#c0392b', 'бой, событие'),
    'station':  ('#2f5d8a', 'станция, погрузка'),
}
RIVER_RU = {'Don': 'Дон', 'Donets': 'Сев. Донец', 'Seversky Donets': 'Сев. Донец',
            'Kuban': 'Кубань', 'Volga': 'Волга', 'Terek': 'Терек', 'Malka': 'Малка',
            'Manych': 'Маныч', 'Sredny Yegorlyk': 'Ср. Егорлык', 'Sal': 'Сал', 'Oskol': 'Оскол',
            'Assa': 'Асса', 'Baksan': 'Баксан', 'Khopr': 'Хопёр', 'Seym': 'Сейм'}
# rivers drawn with named_only=True; other regions add theirs via init(river_ru={'Kama': 'Кама', ...})
OUT, gc, OCEAN, LAKES, RIVERS = '.', {}, [], [], []


def init(geo_dir, geocode_path, out_dir, story=None, lakes=('Caspian',), river_ru=None):
    """Loads Natural Earth layers and coordinates. lakes: only lakes that existed in the period (no later reservoirs)."""
    global OUT, gc, OCEAN, LAKES, RIVERS
    OUT = out_dir
    os.makedirs(OUT, exist_ok=True)
    gc = json.load(open(geocode_path, encoding='utf-8'))
    load = lambda name: json.load(open(os.path.join(os.path.expanduser(geo_dir), name + '.geojson'), encoding='utf-8'))['features']
    OCEAN = load('ne_10m_ocean')
    LAKES = [f for f in load('ne_10m_lakes') if any(n in str(f['properties'].get('name')) for n in lakes)]
    RIVERS = load('ne_10m_rivers_lake_centerlines') + load('ne_10m_rivers_europe')
    if river_ru:
        RIVER_RU.update(river_ru)
    if story:
        for k, v in json.load(open(story, encoding='utf-8')).get('kinds', {}).items():
            KIND[k] = (v['color'], v['label'])


def pt(key):
    p = gc[key][0]
    return p['lon'], p['lat']


def glyph(kind, s=1.0):
    """White glyph centred on 0,0, about 12px across."""
    w = f'stroke="#fff" stroke-width="{1.8*s:.1f}" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    f = 'fill="#fff"'
    if kind == 'home':
        return f'<path d="M-5,0.5 L0,-4.5 L5,0.5 M-3.4,-0.6 V4.4 H3.4 V-0.6" {w}/>'
    if kind == 'birth':
        pts = ' '.join(f'{4.8*math.sin(i*math.pi/5)*(1 if i%2==0 else .45):.1f},{-4.8*math.cos(i*math.pi/5)*(1 if i%2==0 else .45):.1f}' for i in range(10))
        return f'<polygon points="{pts}" {f}/>'
    if kind == 'missing':
        return f'<text x="0" y="4.3" font-size="12" font-weight="700" text-anchor="middle" {f}>?</text>'
    if kind == 'death':
        return f'<path d="M0,-5 V5 M-3.6,-1.8 H3.6" {w}/>'
    if kind == 'pow':
        # handcuffs: two cuffs with hinges and a two-link chain
        ring = f'stroke="#fff" stroke-width="{1.8*s:.1f}" fill="none"'
        link = f'stroke="#fff" stroke-width="{0.85*s:.2f}" fill="none"'
        return (f'<circle cx="-3" cy="-1.6" r="2.4" {ring}/>'
                f'<rect x="-1.95" y="-4.65" width="2.3" height="1.7" rx=".45" {f} transform="rotate(-40 -0.8 -3.8)"/>'
                f'<circle cx="1.05" cy="-4.75" r=".95" {link}/><circle cx="2.75" cy="-3.3" r=".95" {link}/>'
                f'<circle cx="3" cy="2.5" r="2.4" {ring}/>'
                f'<rect x="1.9" y="-1.85" width="2.2" height="1.7" rx=".45" {f} transform="rotate(10 3 -1)"/>')
    if kind == 'division':
        return f'<path d="M-3,5 V-5" {w}/><path d="M-3,-5 L4.5,-2.6 L-3,-0.2 Z" {f}/>'
    if kind == 'event':
        pts = ' '.join(f'{5.2*math.sin(i*math.pi/6)*(1 if i%2==0 else .5):.1f},{-5.2*math.cos(i*math.pi/6)*(1 if i%2==0 else .5):.1f}' for i in range(12))
        return f'<polygon points="{pts}" {f}/>'
    if kind == 'station':
        return (f'<rect x="-4" y="-4.5" width="8" height="7" rx="1.5" {f}/>'
                f'<circle cx="-2.2" cy="4" r="1.2" {f}/><circle cx="2.2" cy="4" r="1.2" {f}/>')
    return ''


def badge(x, y, kind, approx=False, r=9.5):
    col = KIND[kind][0]
    ring = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r+3.5:.1f}" fill="none" stroke="{col}" stroke-width="1.6" stroke-dasharray="3 2.5"/>'
            if approx else '')
    return (f'{ring}<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}" stroke="#fff" stroke-width="1.8"/>'
            f'<g transform="translate({x:.1f},{y:.1f})">{glyph(kind)}</g>')


class Map:
    def __init__(self, lon0, lon1, lat0, lat1, width=900):
        self.lon0, self.lon1, self.lat0, self.lat1 = lon0, lon1, lat0, lat1
        self.k = math.cos(math.radians((lat0 + lat1) / 2))
        self.W = width
        self.s = width / ((lon1 - lon0) * self.k)
        self.H = round((lat1 - lat0) * self.s)
        self.parts, self.top = [], []   # top: drawn above routes (marks, labels)

    def xy(self, lon, lat):
        return (lon - self.lon0) * self.k * self.s, (self.lat1 - lat) * self.s

    def inside(self, lon, lat, pad=1.0):
        return (self.lon0 - pad <= lon <= self.lon1 + pad) and (self.lat0 - pad <= lat <= self.lat1 + pad)

    def path(self, ring, close=False, clamp=False):
        if clamp:
            p = 0.5
            ring = [(min(max(x, self.lon0 - p), self.lon1 + p), min(max(y, self.lat0 - p), self.lat1 + p)) for x, y in ring]
            ring = [q for i, q in enumerate(ring) if i == 0 or q != ring[i - 1]]
        pts = [self.xy(x, y) for x, y in ring]
        if len(pts) < 2:
            return ''
        d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        return d + ('Z' if close else '')

    def polygons(self, feats, fill):
        ds = []
        for f in feats:
            g = f['geometry']
            if not g:
                continue
            polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
            for poly in polys:
                for ring in poly:
                    if any(self.inside(x, y) for x, y in ring[::4]):
                        ds.append(self.path(ring, True, clamp=True))
        if ds:
            self.parts.append(f'<path d="{" ".join(ds)}" fill="{fill}" fill-rule="evenodd" stroke="{RIVER}" stroke-width="0.6"/>')

    def rivers(self, labels=(), named_only=False):
        for f in RIVERS:
            g = f['geometry']
            if not g:
                continue
            if named_only and f['properties'].get('name') not in RIVER_RU:
                continue
            lines = g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]
            for l in lines:
                seg = [p for p in l if self.inside(p[0], p[1], 0.3)]
                if len(seg) > 1:
                    sr = f['properties'].get('scalerank') or 6
                    w = 1.8 if sr <= 3 else 1.1
                    self.parts.append(f'<path d="{self.path(seg)}" fill="none" stroke="{RIVER}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>')
        for name, lon, lat, rot in labels:
            x, y = self.xy(lon, lat)
            self.parts.append(f'<text x="{x:.0f}" y="{y:.0f}" transform="rotate({rot} {x:.0f} {y:.0f})" font-size="13" font-style="italic" fill="{BLUE}" text-anchor="middle">{name}</text>')

    def grid(self, step):
        lon = math.ceil(self.lon0 / step) * step
        while lon < self.lon1:
            x, _ = self.xy(lon, self.lat0)
            self.parts.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{self.H}" stroke="{GRID}" stroke-width="0.7"/>')
            self.parts.append(f'<text x="{x+3:.0f}" y="{self.H-5}" font-size="10" fill="{MUTED}">{lon:g}° в. д.</text>')
            lon += step
        lat = math.ceil(self.lat0 / step) * step
        while lat < self.lat1:
            _, y = self.xy(self.lon0, lat)
            self.parts.append(f'<line x1="0" y1="{y:.1f}" x2="{self.W}" y2="{y:.1f}" stroke="{GRID}" stroke-width="0.7"/>')
            self.parts.append(f'<text x="4" y="{y-3:.0f}" font-size="10" fill="{MUTED}">{lat:g}° с. ш.</text>')
            lat += step

    def sea_label(self, text, lon, lat, size=15):
        x, y = self.xy(lon, lat)
        self.parts.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" font-style="italic" fill="{BLUE}" text-anchor="middle" letter-spacing="1">{text}</text>')

    def route(self, stops, color=ACCENT):
        """Arrow for each leg, shortened so it stops at the badges; numbered step on each stop."""
        pts = [self.xy(*(pt(k) if isinstance(k, str) else k)) for k in stops]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            d = math.hypot(x1 - x0, y1 - y0)
            ux, uy = (x1 - x0) / d, (y1 - y0) / d
            a, b = (x0 + ux * 16, y0 + uy * 16), (x1 - ux * 19, y1 - uy * 19)
            # gentle curve: control point offset to the left of the leg
            cx, cy = (a[0] + b[0]) / 2 - uy * d * 0.12, (a[1] + b[1]) / 2 + ux * d * 0.12
            self.parts.append(f'<path d="M{a[0]:.1f},{a[1]:.1f} Q{cx:.1f},{cy:.1f} {b[0]:.1f},{b[1]:.1f}" fill="none" '
                              f'stroke="#fff" stroke-width="7" stroke-linecap="round" opacity="0.8"/>')
            self.parts.append(f'<path d="M{a[0]:.1f},{a[1]:.1f} Q{cx:.1f},{cy:.1f} {b[0]:.1f},{b[1]:.1f}" fill="none" '
                              f'stroke="{color}" stroke-width="3.2" stroke-linecap="round" marker-end="url(#arrow)"/>')

    def step(self, lonlat, n, pos='tl'):
        x, y = self.xy(*(pt(lonlat) if isinstance(lonlat, str) else lonlat))
        cx = x - 13 if pos[1] == 'l' else x + 13
        cy = y + 13 if pos[0] == 'b' else y - 13
        self.top.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7.5" fill="#fff" stroke="{ACCENT}" stroke-width="1.6"/>'
                        f'<text x="{cx:.1f}" y="{cy+3.4:.1f}" font-size="10" font-weight="700" fill="{ACCENT}" text-anchor="middle">{n}</text>')

    def place(self, lonlat, label, sub=None, kind='home', dx=14, dy=5, anchor='start', approx=False):
        lon, lat = pt(lonlat) if isinstance(lonlat, str) else lonlat
        x, y = self.xy(lon, lat)
        halo = 'paint-order="stroke" stroke="#fbfaf7" stroke-width="3.5" stroke-linejoin="round"'
        if kind == 'ref':
            self.top.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{MUTED}"/>')
            fs, col, fw = 12, MUTED, '400'
            dx = dx if dx != 14 else 7
        else:
            self.top.append(badge(x, y, kind, approx))
            fs, col, fw = 14, INK, '700'
        tx, ty = x + dx, y + dy
        self.top.append(f'<text x="{tx:.0f}" y="{ty:.0f}" font-size="{fs}" font-weight="{fw}" fill="{col}" text-anchor="{anchor}" {halo}>{label}</text>')
        for i, line in enumerate(sub if isinstance(sub, list) else ([sub] if sub else [])):
            self.top.append(f'<text x="{tx:.0f}" y="{ty + 15 + i*14:.0f}" font-size="12" fill="{ACCENT}" text-anchor="{anchor}" {halo}>{line}</text>')

    def scalebar(self, km, at='br'):
        px = km / 111.32 * self.s
        x0, y0 = self.W - px - 20, (self.H - 22 if at == 'br' else 30)
        self.top.append(f'<line x1="{x0:.0f}" y1="{y0}" x2="{x0+px:.0f}" y2="{y0}" stroke="{INK}" stroke-width="2"/>')
        for xx in (x0, x0 + px):
            self.top.append(f'<line x1="{xx:.0f}" y1="{y0-4}" x2="{xx:.0f}" y2="{y0+4}" stroke="{INK}" stroke-width="2"/>')
        self.top.append(f'<text x="{x0+px/2:.0f}" y="{y0-7}" font-size="11" fill="{INK}" text-anchor="middle">{km} км</text>')

    def save(self, fn, legend=(), legend_at='tl', extra=()):
        defs = (f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/></marker>'
                f'<clipPath id="c"><rect width="{self.W}" height="{self.H}"/></clipPath></defs>')
        rows = [(k, KIND[k][1]) for k in legend] + list(extra)
        h = 16 + 24 * len(rows)
        ly = 12 if legend_at == 'tl' else self.H - h - 40
        leg = f'<g transform="translate(12,{ly})"><rect width="232" height="{h}" rx="6" fill="#fbfaf7" fill-opacity="0.94" stroke="#d9d6cf"/>'
        for i, (k, text) in enumerate(rows):
            y = 20 + i * 24
            if k == 'route':
                leg += f'<path d="M8,{y} H34" stroke="{ACCENT}" stroke-width="3.2" marker-end="url(#arrow)"/>'
            elif k == 'approx':
                leg += f'<circle cx="21" cy="{y}" r="9" fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-dasharray="3 2.5"/>'
            elif k == 'step':
                leg += f'<circle cx="21" cy="{y}" r="7.5" fill="#fff" stroke="{ACCENT}" stroke-width="1.6"/><text x="21" y="{y+3.5}" font-size="10" font-weight="700" fill="{ACCENT}" text-anchor="middle">1</text>'
            elif k == 'ref':
                leg += f'<circle cx="21" cy="{y}" r="3.2" fill="{MUTED}"/>'
            else:
                leg += badge(21, y, k, r=8)
            leg += f'<text x="44" y="{y+4}" font-size="12" fill="{INK}">{text}</text>'
        leg += '</g>'
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" width="{self.W}" height="{self.H}" '
               f'font-family="Arial, Helvetica, sans-serif">{defs}<g clip-path="url(#c)">'
               f'<rect width="{self.W}" height="{self.H}" fill="{LAND}"/>{"".join(self.parts)}{"".join(self.top)}</g>'
               f'<rect width="{self.W}" height="{self.H}" fill="none" stroke="#bdb6a8" stroke-width="1.5"/>{leg}</svg>')
        open(os.path.join(OUT, fn), 'w', encoding='utf-8').write(svg)
        print(fn, self.W, 'x', self.H)


def base(m, step):
    m.grid(step)
    m.polygons(OCEAN, WATER)
    m.polygons(LAKES, WATER)
