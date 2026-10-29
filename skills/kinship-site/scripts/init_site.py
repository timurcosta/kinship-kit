"""Prepares a case folder for the live site: config skeletons, git whitelist, deploy workflow. Never overwrites.

Usage: python3 -I init_site.py <case dir> --surname-latin <slug> [--github-user <login>]
Creates (only if missing):
  pdf-source/web/site.json, story.json, version-notes.json   — from the skill's examples, to be filled in
  pdf-source/maps/make_maps.py                                 — layout of static PDF maps (example)
  .gitignore (whitelist), .github/workflows/deploy.yml
and copies stage_public.py next to site.json (CI needs it inside the repo).
"""
import argparse, json, os, secrets, shutil

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument('case')
ap.add_argument('--surname-latin', required=True, help='e.g. ivanovy: used for the bucket, repo and public PDF name')
ap.add_argument('--github-user', default='')
a = ap.parse_args()
CASE = os.path.abspath(a.case)
A = lambda *p: os.path.join(SKILL, 'assets', *p)


def put(rel, text=None, src=None):
    dst = os.path.join(CASE, rel)
    if os.path.exists(dst):
        print('keep  ', rel)
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if src:
        shutil.copy2(src, dst)
    else:
        open(dst, 'w', encoding='utf-8').write(text)
    print('create', rel)


slug = a.surname_latin.lower()
site = json.load(open(A('site.example.json'), encoding='utf-8'))
site['publicPdf'] = f'{slug}-semeynaya-istoriya.pdf'
site['hosting'] = {'bucket': f'{slug}-{secrets.token_hex(5)}', 'repo': f'{a.github_user or "<github-user>"}/{slug}-family'}
site_path = os.path.join(CASE, 'pdf-source', 'web', 'site.json')
put('pdf-source/web/site.json', json.dumps(site, ensure_ascii=False, indent=1))
site = json.load(open(site_path, encoding='utf-8'))
put('pdf-source/web/story.json', src=A('story.example.json'))
put('pdf-source/web/version-notes.json', '{}\n')
put('pdf-source/maps/make_maps.py', src=A('make_maps.example.py'))


def tpl(name):
    """A template with the case PDF filled in; sites with several lines keep their PDFs in web/pdf/, so those lines go."""
    text = open(A(name), encoding='utf-8').read().replace('__BUCKET__', site['hosting']['bucket'])
    if site.get('pdf'):
        return text.replace('__PDF__', site['pdf'])
    return ''.join(l for l in text.splitlines(True) if '__PDF__' not in l)


put('.gitignore', tpl('gitignore'))
put('.github/workflows/deploy.yml', tpl('deploy.yml'))
shutil.copy2(os.path.join(SKILL, 'scripts', 'stage_public.py'), os.path.join(CASE, 'pdf-source', 'web', 'stage_public.py'))
print('synced pdf-source/web/stage_public.py')
print('next: fill site.json and story.json, then geocode.py, make_maps.py, build_pdf.sh, build_web.py, preview.sh')
