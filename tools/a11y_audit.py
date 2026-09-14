#!/usr/bin/env python3
"""
Accessibility audit for the SCIA site (WCAG 2.1 A/AA, per Michigan Tech's
Web Accessibility Procedures), using axe-core in headless Firefox.

Setup (once):
    python3 -m venv .venv && .venv/bin/pip install selenium
    # tools/axe.min.js (axe-core 4.10.2, MPL-2.0) is committed; to update it:
    # curl -sL -o tools/axe.min.js https://cdnjs.cloudflare.com/ajax/libs/axe-core/<version>/axe.min.js

Run (from the site root, with a local server on :8765):
    python3 -m http.server 8765 &
    .venv/bin/python tools/a11y_audit.py http://127.0.0.1:8765

Checks every page in light and dark colour schemes, at desktop width and in
a 320 px / 400 px iframe (WCAG 1.4.10 reflow), and reports axe violations
plus any horizontal overflow. Exit status is non-zero if anything fails.
"""
import json, os, sys, time, tempfile
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://127.0.0.1:8765'
PAGES = ['index.html', 'people.html', 'projects.html', 'publications.html']
HERE = os.path.dirname(os.path.abspath(__file__))
AXE = open(os.path.join(HERE, 'axe.min.js'), encoding='utf-8').read()
TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']
RUN = """var done = arguments[arguments.length-1];
axe.run(document, {runOnly:{type:'tag', values:%s}})
  .then(r => done(JSON.stringify({v:r.violations, i:r.incomplete.length, p:r.passes.length})))
  .catch(e => done(JSON.stringify({error:String(e)})));""" % json.dumps(TAGS)

FRAME = """<!doctype html><meta charset=utf-8><style>body{margin:0}iframe{border:0;display:block}</style>
<iframe id=f width=%d height=900 src="%s"></iframe>"""

failures = 0

def report(label, res, overflow):
    global failures
    v = res.get('violations', res.get('v', []))
    if v or overflow:
        failures += 1
    print(f'{label:46} violations={len(v):<2} needs-review={res.get("i", 0):<2} passed={res.get("p")}  h-overflow={overflow}px')
    for x in v:
        print(f'   [{x["impact"]}] {x["id"]}: {x["help"]}')
        for n in x['nodes'][:5]:
            print('      -', n['target'], '|', n.get('failureSummary', '').replace('\n', ' ')[:200])

def driver(dark):
    o = Options(); o.add_argument('-headless')
    o.set_preference('ui.systemUsesDarkTheme', 1 if dark else 0)
    o.set_preference('layout.css.prefers-color-scheme.content-override', 0 if dark else 1)
    d = webdriver.Firefox(options=o); d.set_window_size(1280, 900); return d

for dark in (False, True):
    theme = 'dark' if dark else 'light'
    d = driver(dark)
    try:
        for p in PAGES:
            d.get(f'{BASE}/{p}'); time.sleep(1.2)
            ov = d.execute_script('return document.documentElement.scrollWidth - document.documentElement.clientWidth')
            d.execute_script(AXE)
            report(f'{theme} {p} @1280px', json.loads(d.execute_async_script(RUN)), ov)
            for w in (400, 320):
                with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as f:
                    f.write(FRAME % (w, f'{BASE}/{p}')); path = f.name
                d.get('file://' + path); time.sleep(1.5)
                d.switch_to.frame(d.find_element(By.ID, 'f'))
                ov = d.execute_script('return document.documentElement.scrollWidth - document.documentElement.clientWidth')
                d.execute_script(AXE)
                report(f'{theme} {p} @{w}px (iframe)', json.loads(d.execute_async_script(RUN)), ov)
                d.switch_to.default_content(); os.unlink(path)
    finally:
        d.quit()

print('\nRESULT:', 'PASS' if failures == 0 else f'FAIL ({failures} run(s) with issues)')
sys.exit(1 if failures else 0)
