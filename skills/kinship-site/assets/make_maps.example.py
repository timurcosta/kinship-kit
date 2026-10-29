"""Static SVG maps for the PDF report of this case: layout only; drawing is in the kinship-site skill (maplib).

Usage: python3 -I make_maps.py <natural-earth dir> <geocode.json> <out dir>
"""
import os, sys

sys.path.insert(0, os.path.expanduser('~/.claude/skills/kinship-site/scripts'))
import maplib as M
from maplib import Map, base, pt

M.init(sys.argv[1], sys.argv[2], sys.argv[3], story=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web', 'story.json'))

# 1. Family places: Map(lon0, lon1, lat0, lat1, width px); base(m, grid step in degrees)
m = Map(46.0, 52.0, 53.5, 56.5, 900)
base(m, 1)
m.rivers([('Волга', 48.9, 55.2, 0)], named_only=True)
m.place('village_key', 'Село', ['кто здесь жил'], kind='home')
m.scalebar(50, at='tr')
m.save('map-family.svg', ['home'], legend_at='bl', extra=[('ref', 'города для ориентира')])
