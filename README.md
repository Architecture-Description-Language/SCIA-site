# SCIA — SCIence in Architecture

Website for the SCIA computer architecture lab (Prof. Soner Önder), Department of
Computer Science, Michigan Technological University. Pronounced “skee-uh”; Latin for *knowledge*.

Plain static HTML/CSS/JS with a tiny build step (Python 3, no dependencies). Serve the folder
with any static file server to preview:

```sh
python3 build.py                 # regenerate *.html and publications.bib from src/
python3 -m http.server 8765      # then visit http://127.0.0.1:8765/
```

## How the site is put together

```
src/layout.html          Shared page shell: <head>, header/nav, footer. Edit here, not in *.html.
src/pages/*.html         One file per page: a front-matter comment (title, description, nav)
                         followed by the page body, which lands inside <main>.
src/data/publications.json   The publication list. build.py renders it into publications.html
                         (grouped by year, newest first) and into publications.bib.
build.py                 Assembles the above into the committed index.html, people.html,
                         projects.html, publications.html and publications.bib.
assets/css/style.css     All styling; palette tokens at the top (light + dark scheme).
assets/js/main.js        Mobile nav, carousel, publication filter.
assets/img/              logo-160.png (nav/footer) · logo-600.png/.webp (About card) ·
                         logo-full.png (full-res badge; built by tools/make_badge.py from the
                         Gemini render kept outside git in backups/) ·
                         favicon.svg / favicon.ico / apple-touch-icon.png (the chip-medallion icon;
                         medallion.svg is the detailed vector master, icon-512.png a large PNG) ·
                         photos/ (carousel, 1000 px + 1800 px) · people/ (headshots 340×460)
tools/a11y_audit.py      Accessibility audit (axe-core in headless Firefox) — see below.
```

**The generated `*.html` files are committed** so the university web space can serve the
folder as-is. After editing anything under `src/`, run `python3 build.py` and commit both the
source and the output.

## Editing content

**News** — `src/pages/index.html`, the `<ol class="news">` list. One `<li>` per item:
`<li><time datetime="2026-06">June 2026</time><span>…</span></li>`. Newest first; keep to a line or two.

**A publication** — add an object to `src/data/publications.json`:

```json
{ "year": 2026, "type": "conference",
  "title": "Paper Title", "authors": ["First Author", "Soner Önder"],
  "abbr": "ISCA 2026", "venue": "Proceedings of the 53rd International Symposium on Computer Architecture",
  "pages": "1–12", "doi": "10.1145/…", "pdf": "https://…/paper.pdf",
  "links": [{"label": "Slides", "url": "https://…"}] }
```

`type` is one of `conference`, `journal`, `chapter`, `thesis`, `report`, `patent`. `pages`, `doi`,
`pdf`, `links` are optional; the title links to the DOI (or the first link / PDF). Run `build.py`.

**A person** — `src/pages/people.html`: copy an `<article class="card person">` block, add a
340×460 headshot to `assets/img/people/`, keep `alt="Portrait of …"`. The roster follows the
*Current Students* column on Prof. Önder's page.

**When someone graduates** — move them to the Alumni section (year, name, dissertation link,
`alumni-now` line, or a name in the Master's list) and add the thesis to `publications.json`.

**A project** — `src/pages/projects.html`: copy an `<article class="card project">`. Badges:
`badge` (neutral), `badge active` (green). Links to `publications.html?q=term` pre-filter the list.

**Carousel photos** — export 1800 px and 1000 px wide JPEGs into `assets/img/photos/`, then edit
the `<figure class="slide">` blocks in `src/pages/index.html` (keep `srcset`, a real `alt`, and
update the `aria-label="n of N"` counts and the dot buttons if the number of slides changes).
Use `class="crop-lower"` / `crop-bottom` on 4:3 photos to bias the crop toward the bottom.

## TODO

- Josh Pearlman's research blurb is a placeholder (`people.html`).
- Set an absolute `og:image` in `src/layout.html` once the final URL is known.
- Confirm current positions for Zhaoxiang Jin and Shuhan Ding (both from LinkedIn headlines);
  add positions for Hui Meen Nyew and Peng Zhou if known.

## Accessibility (Michigan Tech policy)

Michigan Tech's Web Accessibility Procedures require WCAG 2.1 Level A/AA. The site was built and
audited to that standard:

- Semantic landmarks (`header`/`nav`/`main`/`footer`), a skip link, one `h1` per page, no skipped heading levels.
- Text contrast ≥ 4.5:1 for all text in both light and dark colour schemes (photo captions sit on an overlay verified at ≥ 11:1).
- Fully keyboard operable, visible focus rings, 24 px minimum targets for controls.
- Carousel: WAI-ARIA carousel pattern; auto-rotation pauses on hover/focus, has an explicit Pause/Play
  button (WCAG 2.2.2), never starts under `prefers-reduced-motion`, and the live region only announces
  slides the user picks.
- Reflows without horizontal scrolling down to 320 px (WCAG 1.4.10); relative units throughout.
- Alt text on every image (decorative logo instances are `alt=""`); repeated link text (“Website”,
  “NSF award page”) carries a distinct accessible name.

Re-run the audit after content changes:

```sh
python3 -m venv .venv && .venv/bin/pip install selenium   # once; needs Firefox installed
python3 -m http.server 8765 &
.venv/bin/python tools/a11y_audit.py http://127.0.0.1:8765
```

It checks every page in light and dark schemes at desktop width and inside 320/400 px frames and
exits non-zero on any axe violation or horizontal overflow.

## Hosting / deploying

The site is served from Michigan Tech web space (`/Volumes/Multidrive/my_web_files/SCIA-site/`
when the Multidrive share is mounted). All paths are relative, so it works at any URL; only the
Google Fonts stylesheet is loaded from outside the site, with system-font fallbacks.

Two ways to publish:

**Without the VPN (from campus Wi-Fi):**

```sh
tools/deploy_via_ssh.sh            # builds, rsyncs to colossus, pushes with smbclient
```

The file server is not reachable from the campus Wi-Fi network, but `colossus.it.mtu.edu` is,
and it can reach the server. The script stages the referenced files, rsyncs them to
`~/.scia-site-deploy` on colossus (via the `colossusw` SSH host, which pins traffic to Wi-Fi),
and runs `smbclient` there. The SMB password is read from the Mac Keychain (the entry Finder
saved for `multidrive.mtu.edu`) and piped over SSH — it is never stored on the server. macOS
will ask once to allow `security` to read the Keychain item. Pass a different SSH host as the
first argument (e.g. `tools/deploy_via_ssh.sh colossus` when the VPN is up).

**With the VPN or wired:** mount the share (Finder → Go → Connect to Server →
`smb://multidrive.mtu.edu`), then

```sh
python3 build.py --deploy          # builds, then copies only the referenced files
```
