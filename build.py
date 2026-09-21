#!/usr/bin/env python3
"""Build the SCIA site: src/pages/*.html + src/layout.html -> ./*.html
and src/data/publications.json -> the publication list + publications.bib,
plus sitemap.xml and robots.txt for the canonical BASE_URL.

    python3 build.py

    python3 build.py --deploy [DEST]   # also copy the site to the web space
                                       # (default DEST: the Multidrive SCIA-site folder)

No dependencies. Each page in src/pages/ starts with a comment block of
`key: value` lines (title, description, nav) followed by the page body,
which is dropped into <main> of src/layout.html. A page may contain the
placeholders {{publications}}, {{year_nav}} and {{pub_count}}.

--deploy copies only what the pages reference (HTML, .bib, CSS, JS, the
images actually used) — not src/, tools/, backups/ or the unreferenced
full-size logo. It refuses to run if DEST's volume is not mounted.
"""
import datetime, json, os, re, shutil, sys, unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
NAV = [('people', 'People', 'people.html'),
       ('projects', 'Projects', 'projects.html'),
       ('publications', 'Publications', 'publications.html')]
SITE = 'SCIA — SCIence in Architecture'
# Where the site officially lives (GitHub Pages): used for <link rel="canonical">, og:url,
# og:image, sitemap.xml and robots.txt. Index page = the bare base URL.
BASE_URL = 'https://architecture-description-language.github.io/SCIA-site/'

def e(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# ---------------------------------------------------------------- publications
def pub_html(p, key):
    doi = p.get('doi')
    links = p.get('links', [])
    primary = ('https://doi.org/' + doi) if doi else (links[0]['url'] if links else p.get('pdf'))
    # Every outbound link of an entry counts as the GoatCounter event "paper/<key>"
    # (see the analytics note in src/layout.html), so the dashboard shows which papers get opened.
    track = f' data-goatcounter-click="paper/{e(key)}" data-goatcounter-title="{e(p["title"])}"'
    title = (f'<a class="title" href="{e(primary)}"{track}>{e(p["title"])}</a>' if primary
             else f'<span class="title">{e(p["title"])}</span>')
    venue = f'<span class="abbr">{e(p["abbr"])}</span> · {e(p["venue"])}'
    if p.get('pages'):
        venue += f', pp. {e(p["pages"])}'
    pills = []
    if doi:
        pills.append(f'<a href="https://doi.org/{e(doi)}"{track}>DOI</a>')
    pills += [f'<a href="{e(l["url"])}"{track}>{e(l["label"])}</a>' for l in links]
    if p.get('pdf'):
        pills.append(f'<a href="{e(p["pdf"])}"{track}>PDF</a>')
    pills_html = f'\n            <div class="pub-links">{"".join(pills)}</div>' if pills else ''
    return (f'          <li class="pub" data-type="{e(p["type"])}">\n'
            f'            {title}\n'
            f'            <div class="authors">{", ".join(e(a) for a in p["authors"])}</div>\n'
            f'            <div class="venue">{venue}</div>{pills_html}\n'
            f'          </li>')

def render_publications(pubs):
    years = sorted({p['year'] for p in pubs}, reverse=True)
    keyed = list(zip(pubs, cite_keys(pubs)))
    groups = []
    for y in years:
        items = '\n'.join(pub_html(p, k) for p, k in keyed if p['year'] == y)
        groups.append(f'      <section class="pub-group" id="y{y}" aria-labelledby="h{y}">\n'
                      f'        <h2 id="h{y}">{y}</h2>\n        <ol>\n{items}\n        </ol>\n      </section>')
    year_nav = ''.join(f'<li><a href="#y{y}">{y}</a></li>' for y in years)
    return '\n'.join(groups), year_nav

def cite_keys(pubs):
    """One key per entry, e.g. Onder2026title (first author, year, first title word), made
    unique with a/b/c suffixes. Used for BibTeX keys and to name the paper click events."""
    def ascii_(s):
        s = s.translate(str.maketrans('ıİşŞğĞçÇ', 'iIsSgGcC'))
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    keys, seen = [], {}
    for p in pubs:
        last = re.sub(r'[^A-Za-z]', '', ascii_(p['authors'][0].split()[-1])) or 'Anon'
        word = re.sub(r'[^A-Za-z]', '', p['title'].split()[0]) or 'x'
        k = f'{last}{p["year"]}{word.lower()}'
        seen[k] = seen.get(k, 0) + 1
        keys.append(k + (chr(ord('a') + seen[k] - 1) if seen[k] > 1 else ''))
    return keys

def bibtex(pubs):
    def f(k, v):
        return f'  {k} = {{{v}}},\n'
    out = []
    for p, k in zip(pubs, cite_keys(pubs)):
        kind = {'conference': 'inproceedings', 'journal': 'article', 'chapter': 'incollection',
                'thesis': 'phdthesis', 'report': 'techreport', 'patent': 'misc'}[p['type']]
        s = f'@{kind}{{{k},\n' + f('title', p['title']) + f('author', ' and '.join(p['authors'])) + f('year', p['year'])
        if kind == 'inproceedings': s += f('booktitle', p['venue'])
        elif kind == 'article': s += f('journal', p['venue'])
        elif kind == 'incollection': s += f('booktitle', re.sub(r'^In ', '', p['venue']))
        elif kind == 'phdthesis': s += f('school', 'Michigan Technological University')
        elif kind == 'techreport': s += f('institution', p['venue'])
        else: s += f('howpublished', p['abbr']) + f('note', p['venue'])
        if p.get('pages'): s += f('pages', p['pages'].replace('–', '--'))
        if p.get('doi'): s += f('doi', p['doi'])
        url = p.get('pdf') or (p['links'][0]['url'] if p.get('links') else None)
        if url and not p.get('doi'): s += f('url', url)
        out.append(s.rstrip(',\n') + '\n}\n')
    return '\n'.join(out)

# ---------------------------------------------------------------- pages
def parse_page(path):
    s = open(path, encoding='utf-8').read()
    m = re.match(r'\s*<!--(.*?)-->\s*\n', s, flags=re.S)
    if not m:
        sys.exit(f'{path}: missing front-matter comment block')
    meta = dict(re.findall(r'^\s*([a-z_]+):\s*(.*?)\s*$', m.group(1), flags=re.M))
    return meta, s[m.end():].rstrip()

def build():
    layout = open(os.path.join(SRC, 'layout.html'), encoding='utf-8').read()
    pubs = json.load(open(os.path.join(SRC, 'data', 'publications.json'), encoding='utf-8'))
    pubs.sort(key=lambda p: -p['year'])
    groups_html, year_nav = render_publications(pubs)
    open(os.path.join(ROOT, 'publications.bib'), 'w', encoding='utf-8').write(bibtex(pubs))
    year = str(datetime.date.today().year)
    urls = []
    for name in sorted(os.listdir(os.path.join(SRC, 'pages'))):
        if not name.endswith('.html'):
            continue
        meta, body = parse_page(os.path.join(SRC, 'pages', name))
        canonical = BASE_URL + ('' if name == 'index.html' else name)
        urls.append(canonical)
        body = (body.replace('{{publications}}', groups_html)
                    .replace('{{year_nav}}', year_nav)
                    .replace('{{pub_count}}', str(len(pubs))))
        nav = '\n'.join('        <li><a href="%s"%s>%s</a></li>' % (href, ' aria-current="page"' if meta.get('nav') == key else '', label)
                        for key, label, href in NAV)
        page = (layout.replace('{{title}}', e(meta['title']))
                      .replace('{{og_title}}', e(meta.get('og_title', meta['title'])))
                      .replace('{{description}}', e(meta['description']))
                      .replace('{{canonical}}', canonical)
                      .replace('{{base_url}}', BASE_URL)
                      .replace('{{nav}}', nav)
                      .replace('{{year}}', year)
                      .replace('{{content}}', body))
        open(os.path.join(ROOT, name), 'w', encoding='utf-8').write(page)
        print('built', name)
    print('built publications.bib', f'({len(pubs)} entries)')
    # sitemap + robots.txt for search engines (Google Search Console asks for the sitemap URL)
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + ''.join(f'  <url><loc>{u}</loc></url>\n' for u in urls) + '</urlset>\n')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(sitemap)
    open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8').write(
        f'User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n')
    print('built sitemap.xml, robots.txt', f'({len(urls)} pages)')

DEPLOY_DEFAULT = '/Volumes/Multidrive/my_web_files/SCIA-site'

def deploy(dest):
    vol = os.sep.join(dest.split(os.sep)[:3]) if dest.startswith('/Volumes/') else os.path.dirname(dest)
    if not os.path.isdir(vol):
        sys.exit(f'deploy: {vol} is not mounted (connect to smb://multidrive.mtu.edu first)')
    pages = ['index.html', 'people.html', 'projects.html', 'publications.html']
    files = set(pages) | {'publications.bib'}
    for pg in pages:
        s = open(os.path.join(ROOT, pg), encoding='utf-8').read()
        files |= set(re.findall(r'(?:src|href)="(assets/[^"]+)"', s))
        files |= {u.strip().split(' ')[0] for ss in re.findall(r'srcset="([^"]+)"', s) for u in ss.split(',')}
    css = open(os.path.join(ROOT, 'assets', 'css', 'style.css')).read()
    files |= {'assets/' + u.strip('\'"') for u in re.findall(r'url\(([^)]+)\)', css) if not u.startswith(('http', 'data', '#'))}
    files = sorted(f for f in files if os.path.exists(os.path.join(ROOT, f)))
    copied = 0
    for f in files:
        src, dst = os.path.join(ROOT, f), os.path.join(dest, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src) or open(src, 'rb').read() != open(dst, 'rb').read():
            shutil.copy2(src, dst); copied += 1
    print(f'deploy: {len(files)} files checked, {copied} copied to {dest}')

if __name__ == '__main__':
    build()
    if '--deploy' in sys.argv:
        i = sys.argv.index('--deploy')
        deploy(sys.argv[i + 1] if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith('-') else DEPLOY_DEFAULT)
