"""Copies web/ into a staging folder ready for public hosting, with old versions from git.
Part of the kinship-site skill; cases keep a copy at pdf-source/web/stage_public.py for CI (build_web.py syncs it).

Usage: python3 -I stage_public.py <case dir> <stage dir>
Originals in scans/ stay local: «Оригинал» points to the web copy; search engines are told not to index.
Each commit that brought new information (text, people, places, events) becomes a version; look-only commits fold into it.
Snapshots go to v/<id>/ (images and unchanged scripts are shared
with the current site) plus v/<id>/sections.json with the report text; versions.json lists them newest first.
"""
import datetime, difflib, html, json, os, re, shutil, subprocess, sys
from html.parser import HTMLParser

CASE, STAGE = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
SITE = json.load(open(os.path.join(CASE, 'pdf-source', 'web', 'site.json'), encoding='utf-8'))
PDF = SITE.get('pdf')                 # file name in the case folder (sites with several lines keep their PDFs in web/pdf/)
PUBLIC_PDF = SITE.get('publicPdf')    # latin name it gets on the site
SHARED = ('img/', 'assets/vendor/', 'pdf/')   # served once from the site root, never deleted on deploy
LANGS = SITE.get('langs') or [None]
# (page, data file, language) for every language page; the first language is index.html
PAGES = [('index.html' if l == LANGS[0] else f'{l}.html', 'data/story.js' if l == LANGS[0] else f'data/story.{l}.js', l or 'ru') for l in LANGS]


def publicize(d, root=''):
    """Rewrites a built web/ copy for hosting; root is the path from d back to the site root."""
    for page, data, _ in PAGES:
        publicize_page(d, page, data, root)


def publicize_page(d, page_rel, data_rel, root):
    fn = os.path.join(d, data_rel)
    out = []
    for line in open(fn, encoding='utf-8').read().splitlines():
        if line.startswith('window.GALLERY='):
            arr = json.loads(line[len('window.GALLERY='):-1])
            for g in arr:
                g['full'] = g['src']
            line = 'window.GALLERY=' + json.dumps(arr, ensure_ascii=False, separators=(',', ':')) + ';'
        out.append(line)
    js = '\n'.join(out) + '\n'
    if root:
        js = js.replace('"img/', f'"{root}img/')
    open(fn, 'w', encoding='utf-8').write(js)

    page = os.path.join(d, page_rel)
    h = open(page, encoding='utf-8').read()
    if PDF:
        h = h.replace(f'href="../{PDF}"', f'href="{root}{PUBLIC_PDF}"')
    h = h.replace('<meta name="theme-color"', '<meta name="robots" content="noindex, nofollow, noarchive">\n<meta name="theme-color"', 1)
    if root:
        h = re.sub(r'((?:src|href|data-lb)=")((?:img|assets/vendor|pdf)/)', rf'\1{root}\2', h)
    open(page, 'w', encoding='utf-8').write(h)

    local = [f for f in (data_rel, page_rel) if '"../' in open(os.path.join(d, f), encoding='utf-8').read().replace(f'"{root}', '"')]
    if local:
        sys.exit(f'local paths left in {d}: {local}')


class Sections(HTMLParser):
    """Report text by h2 section: one string per paragraph, list item, table row, quote or caption."""
    BLOCKS = {'p', 'li', 'tr', 'blockquote', 'figcaption', 'h3', 'h4'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0          # nesting inside article#report-body
        self.secs = [{'id': '', 'title': 'Начало отчёта', 'blocks': []}]
        self.block = None       # [tag, depth, text parts]
        self.h2 = None
        self.prefix = ''        # «Line · » when the page holds a report per family line

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self.depth:
            if tag == 'article' and (a.get('id') or '').startswith('report-body'):
                self.depth = 1
                self.prefix = a['data-title'] + ' · ' if a.get('data-title') else ''
            return
        if tag in ('br', 'img', 'hr', 'meta', 'input', 'source'):
            if tag == 'img' and self.block is None and a.get('alt'):
                self.secs[-1]['blocks'].append(f'[изображение: {a["alt"]}]')
            return
        self.depth += 1
        if tag == 'h2':
            self.h2 = [a.get('id', ''), []]
        elif self.block is None and self.h2 is None and tag in self.BLOCKS:
            self.block = [tag, self.depth, []]
        elif self.block and tag in ('td', 'th') and self.block[2]:
            self.block[2].append(' | ')

    def handle_endtag(self, tag):
        if not self.depth or tag in ('br', 'img', 'hr', 'meta', 'input', 'source'):
            return
        if self.h2 is not None and tag == 'h2':
            self.secs.append({'id': self.h2[0], 'title': self.prefix + norm(''.join(self.h2[1])), 'blocks': []})
            self.h2 = None
        elif self.block and self.depth == self.block[1]:
            t = norm(''.join(self.block[2]))
            if t:
                self.secs[-1]['blocks'].append(t)
            self.block = None
        self.depth -= 1

    def handle_data(self, data):
        if self.h2 is not None:
            self.h2[1].append(data)
        elif self.block is not None:
            self.block[2].append(data)


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def sections(index_html):
    p = Sections()
    p.feed(index_html)
    return [s for s in p.secs if s['blocks'] or s['id']]


def changes(old, new):
    """Per-section summary: [{title, kind, plus, minus}] for sections whose text differs."""
    om = {s['title']: s['blocks'] for s in old}
    nt = {s['title'] for s in new}
    res = []
    for s in new:
        if s['title'] not in om:
            res.append({'title': s['title'], 'kind': 'added', 'plus': len(s['blocks']), 'minus': 0})
            continue
        plus = minus = 0
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, om[s['title']], s['blocks'], autojunk=False).get_opcodes():
            if op != 'equal':
                minus += i2 - i1
                plus += j2 - j1
        if plus or minus:
            res.append({'title': s['title'], 'kind': 'changed', 'plus': plus, 'minus': minus})
    for s in old:
        if s['title'] not in nt:
            res.append({'title': s['title'], 'kind': 'removed', 'plus': 0, 'minus': len(s['blocks'])})
    return res


def git(*args, binary=False):
    r = subprocess.run(['git', '-C', CASE, *args], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode('utf-8')


def blob_ids(rev):
    out = {}
    for line in git('ls-tree', '-r', rev, '--', 'web').splitlines():
        meta, path = line.split('\t', 1)
        out[path[len('web/'):]] = meta.split()[2]
    return out


def page_text(h, story_js):
    """Everything a reader would call information: report sections, plus the page head, family tree and map texts.
    Map geometry, icons and styles are left out, so redrawing an arrow is not a new version."""
    strip = lambda s: norm(html.unescape(re.sub(r'<[^>]+>', ' ', s)))
    head = [strip(x) for x in re.findall(r'<title>(.*?)</title>', h, re.S)[:1] + re.findall(r'<p class="kicker">(.*?)</p>', h, re.S)[:1]
            + re.findall(r'<h1>(.*?)</h1>', h, re.S)[:1] + re.findall(r'<div class="fact card">(.*?)</div>', h, re.S)
            + re.findall(r'<div class="person card[^"]*"[^>]*>(.*?)</div>', h, re.S)
            + re.findall(r'<p class="lede">(.*?)</p>', h, re.S)[:1] + re.findall(r'<ul class="lc-facts">(.*?)</ul>', h, re.S)]
    story = {}
    for line in story_js.splitlines():
        if line.startswith('window.STORY='):
            story = json.loads(line[len('window.STORY='):].rstrip().rstrip(';'))
    mp = []
    for p in story.get('places', []):
        mp.append(p['name'])
        mp += [norm(f"{p['name']}: {e.get('date', '')} {e['text']}") for e in p.get('events', [])]
    mp += [norm(f"{s['date']}. {s['title']}. {s['text']} «{s.get('quote', '')}» ({s.get('src', '')})") for s in story.get('steps', [])]
    mp += [norm(f"{f['label']}: {f.get('text', '')} ({f.get('src', '')})") for f in story.get('front', [])]
    return ([{'id': '', 'title': 'Главная страница и семья', 'blocks': [x for x in head if x]}] + sections(h)
            + [{'id': '', 'title': 'Карта: места и события', 'blocks': mp}])


def build_versions():
    """A version is a commit that brought new information; later commits that only changed the look
    (arrows, icons, layout, engine) are folded into it: the snapshot shows the last state of the group,
    the date and title are those of the commit with the new information."""
    log = git('-c', 'core.quotepath=false', 'log', '--reverse', '--format=%H%x1f%cI%x1f%s', '--', 'web', *([PDF] if PDF else [])).strip()
    if not log:
        return
    commits = [l.split('\x1f') for l in log.splitlines()]
    nf = os.path.join(CASE, 'pdf-source', 'web', 'version-notes.json')   # {"sha7": "title"} or {"sha7": {"title", "show"}}
    notes = json.load(open(nf, encoding='utf-8')) if os.path.exists(nf) else {}
    note = lambda vid: notes.get(vid) if isinstance(notes.get(vid), dict) else ({'title': notes[vid]} if vid in notes else {})
    texts, groups, other = [], [], []   # other: texts of the other language pages, for their own «what changed»
    for i, (sha, date, title) in enumerate(commits):
        show = lambda rel: git('show', f'{sha}:web/{rel}', binary=True).decode('utf-8')
        texts.append(page_text(show('index.html'), show('data/story.js')))
        other.append({})
        for page, data, lang in PAGES[1:]:
            try:
                other[-1][lang] = page_text(show(page), show(data))
            except subprocess.CalledProcessError:   # the page did not exist yet
                pass
        n = note(sha[:7])
        news = i == 0 or bool(changes(texts[-2], texts[-1]))
        if n.get('show', news):
            groups.append({'start': i, 'end': i, 'title': n.get('title', title), 'date': date})
        else:
            groups[-1]['end'] = i
    versions = []
    for g in groups:
        sha = commits[g['end']][0]
        snapshot(sha, g['title'], g['date'])
        json.dump(texts[g['end']], open(os.path.join(STAGE, 'v', sha[:7], 'sections.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        for lang, tx in other[g['end']].items():
            json.dump(tx, open(os.path.join(STAGE, 'v', sha[:7], f'sections.{lang}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        versions.append({'id': sha[:7], 'date': g['date'], 'title': g['title'], 'commits': g['end'] - g['start'] + 1})
    for i, v in enumerate(versions):
        v['changes'] = changes(texts[groups[i - 1]['end']], texts[groups[i]['end']]) if i else None
    versions.reverse()
    json.dump({'versions': versions}, open(os.path.join(STAGE, 'versions.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('versions', len(versions), 'from', len(commits), 'commits')


def snapshot(sha, title, date):
    vid = sha[:7]
    d = os.path.join(STAGE, 'v', vid)
    for path, blob in blob_ids(sha).items():
        if path.startswith(SHARED):
            continue
        data = git('cat-file', 'blob', blob, binary=True)
        cur = os.path.join(STAGE, path)
        if path not in [x for pg in PAGES for x in pg[:2]] and os.path.exists(cur) and open(cur, 'rb').read() == data:
            continue        # identical to the current file: the snapshot links to the root copy
        fn = os.path.join(d, path)
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        open(fn, 'wb').write(data)
    present = [pg for pg in PAGES if os.path.exists(os.path.join(d, pg[0]))]
    for page_rel, data_rel, _ in present:
        publicize_page(d, page_rel, data_rel, '../../')
    when = datetime.datetime.fromisoformat(date)
    for page_rel, _, lang in present:
        page = os.path.join(d, page_rel)
        h = open(page, encoding='utf-8').read()
        for path in ('assets/app.css', 'assets/app.js', 'data/geo.js'):
            if not os.path.exists(os.path.join(d, path)):
                h = h.replace(f'="{path}"', f'="../../{path}"')
        B = BANNER.get(lang, BANNER['ru'])
        t = title.get(lang) or next(iter(title.values())) if isinstance(title, dict) else title
        here = '' if page_rel == 'index.html' else page_rel
        banner = ('<div style="background:#7a2e1f;color:#fff;font:14px/1.45 -apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,Arial,sans-serif;'
                  'padding:9px 16px;text-align:center">'
                  + B['old'].format(d=f'{when.day} {B["months"][when.month - 1]} {when.year}, {when:%H:%M}', t=html.escape(t)) + ' '
                  f'<a href="../../{here}" style="color:#fff;font-weight:700">{B["current"]}</a> · '
                  f'<a href="../../{here}#versions" style="color:#fff">{B["all"]}</a></div>')
        h = re.sub(r'<body([^>]*)>', lambda m: m.group(0) + '\n' + banner, h, count=1)
        open(page, 'w', encoding='utf-8').write(h)


MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
BANNER = {'ru': {'old': 'Это старая версия от {d} — «{t}». PDF по ссылке — актуальный.', 'current': 'Открыть актуальную версию', 'all': 'все версии', 'months': MONTHS},
          'ka': {'old': 'ეს ძველი ვერსიაა, {d} — «{t}». PDF ბმულით მიმდინარეა.', 'current': 'მიმდინარე ვერსიის გახსნა', 'all': 'ყველა ვერსია',
                 'months': ['იანვარი', 'თებერვალი', 'მარტი', 'აპრილი', 'მაისი', 'ივნისი', 'ივლისი', 'აგვისტო', 'სექტემბერი', 'ოქტომბერი', 'ნოემბერი', 'დეკემბერი']}}

if os.path.exists(STAGE):
    shutil.rmtree(STAGE)
shutil.copytree(os.path.join(CASE, 'web'), STAGE)
if PDF:
    shutil.copy2(os.path.join(CASE, PDF), os.path.join(STAGE, PUBLIC_PDF))
publicize(STAGE)
open(os.path.join(STAGE, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
if os.path.isdir(os.path.join(CASE, '.git')):
    build_versions()
print('staged', STAGE)
