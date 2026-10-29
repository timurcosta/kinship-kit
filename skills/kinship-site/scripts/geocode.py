"""Adds coordinates for story.json places that are not yet in pdf-source/maps/geocode.json (OpenStreetMap Nominatim).

Usage: python3 -I geocode.py <case dir>
Each place is searched by its "q" (search text), else by its "name"; keep "q" specific: «Ассиновская, Чечня».
Nominatim rules: at most 1 request per second, an identifying User-Agent, results cached (geocode.json).
Check every result on the map: villages with the same name are common, and historical places may be gone.
"""
import json, os, sys, time, urllib.parse, urllib.request

CASE = os.path.abspath(sys.argv[1])
story = json.load(open(os.path.join(CASE, 'pdf-source', 'web', 'story.json'), encoding='utf-8'))
site = json.load(open(os.path.join(CASE, 'pdf-source', 'web', 'site.json'), encoding='utf-8'))
fn = os.path.join(CASE, 'pdf-source', 'maps', 'geocode.json')
os.makedirs(os.path.dirname(fn), exist_ok=True)
gc = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else {}
skip = set(site.get('placeOverrides', {}))
UA = 'kinship-research-map/1.0 (personal genealogy report)'

for p in story['places']:
    if p['key'] in gc or p['key'] in skip:
        continue
    q = p.get('q') or p['name'].replace('≈', '').replace('[?]', '').strip()
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 3, 'accept-language': 'ru'})
    res = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30))
    gc[p['key']] = [{'name': r['display_name'], 'lat': float(r['lat']), 'lon': float(r['lon']), 'type': r.get('type'), 'cls': r.get('class')} for r in res]
    print(p['key'], '←', q, '→', gc[p['key']][0]['name'] if res else 'NOT FOUND')
    json.dump(gc, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    time.sleep(1.1)
missing = [k for k, v in gc.items() if not v]
if missing:
    print('not found (add "q" or placeOverrides):', missing)
