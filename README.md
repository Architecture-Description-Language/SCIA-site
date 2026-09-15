# SCIA — SCIence in Architecture

Website for the SCIA computer architecture lab (Prof. Soner Önder), Department of
Computer Science, Michigan Technological University. Pronounced “skee-uh”; Latin for *knowledge*.

Plain static HTML/CSS/JS — no build step, no dependencies. Open `index.html` in a browser
or serve the folder with any static file server:

```sh
python3 -m http.server 8765      # then visit http://127.0.0.1:8765/
```

## Layout

```
index.html            Home: nav, group-photo carousel, About, research themes
people.html           PI, current doctoral students, and alumni (dissertations + where they are now)
projects.html         Current and earlier projects (NSF awards, FAST, IRES/NTNU)
publications.html     Publications by year with a live text filter (?q=… works too)
assets/css/style.css  All styling; palette tokens at the top (light + dark scheme)
assets/js/main.js     Mobile nav, carousel, publication filter
assets/img/
  logo-160.png        Nav/footer logo          logo-600.png / .webp  About-card emblem
  logo-full.png       Full-resolution transparent logo (source only; not used by pages)
  favicon*.png, apple-touch-icon.png
  photos/             Carousel photos, 1000 px and 1800 px wide (JPEG q82)
  people/             Headshots (340×460, from the MTU directory)
tools/a11y_audit.py   Accessibility audit (axe-core in headless Firefox) — see below
```

## Editing content

**Add or change a person** — copy an `<article class="card person">` block in `people.html`,
add a 340×460 headshot to `assets/img/people/`, and keep `alt="Portrait of …"`. The
roster follows the *Current Students* column on Prof. Önder's page.

**When someone graduates** — move them to the Alumni section in `people.html`: copy an
`<li>` in the doctoral list (year, name, dissertation link, `alumni-now` line) or add a name to
the Master's list, and add the thesis to `publications.html` under its year.

**Add a publication** — add an `<li class="pub">` inside the right `<section class="pub-group" id="yYYYY">`
in `publications.html` (create the year section and its `year-nav` link if needed). Each entry
is: title link (DOI preferred) → authors → venue (`<span class="abbr">` for the short name) → link pills.
The filter needs no changes.

**Add a project** — copy an `<article class="card project">` in `projects.html`. Badges: `badge`
(neutral), `badge active` (green). Links to `publications.html?q=term` pre-filter the publication list.

**Swap carousel photos** — export a 1800 px and a 1000 px wide JPEG into `assets/img/photos/`,
then edit the `<figure class="slide">` blocks in `index.html` (keep `srcset`, a meaningful `alt`,
and update the `aria-label="n of N"` counts and the dot buttons if the number of slides changes).

## Deploying

Upload the whole folder (except `tools/` and `README.md` if you like) to the web space,
e.g. `pages.mtu.edu/~soner/scia/` or a departmental host. All paths are relative, so the site
works at any URL. Only the Google Fonts stylesheet is loaded from outside the site; if it is ever
blocked the system font fallbacks in `style.css` take over.

## Accessibility (Michigan Tech policy)

Michigan Tech's Web Accessibility Procedures require WCAG 2.1 Level A/AA. The site was built and
audited to that standard:

- Semantic landmarks (`header`/`nav`/`main`/`footer`), a skip link, one `h1` per page, no skipped heading levels.
- Text contrast ≥ 4.5:1 for all text in both light and dark colour schemes (photo captions sit on an overlay verified at ≥ 12:1).
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
