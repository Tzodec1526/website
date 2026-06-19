# tomcedoz.com

A quiet resource hub for in-house counsel: checklists, frameworks, decision trees,
and quick-reference guides for employment defense, commercial litigation, and AI
legal risk.

The site itself is plain HTML and CSS — no framework, no runtime build, no required
JavaScript. The small local script in `assets/site.js` wires print buttons and
progressive reveal animation; everything works with JS disabled. Two **build-time**
Python scripts generate the resource pages and the SEO layer; their output is
committed as static files, so the deployed site is still just HTML/CSS/assets.

## License

Two licenses, by design — code and content are different things:

- **Site code** — the HTML, CSS, JavaScript, and the Python build scripts — is
  under the **MIT License** ([`LICENSE`](LICENSE)).
- **Content** — the resources, the article, and the other prose — is under
  **Creative Commons Attribution-ShareAlike 4.0** ([`LICENSE-content`](LICENSE-content)):
  use and adapt it freely, even commercially; if you **republish** it, keep the
  credit and share your version under the same license. (Using a checklist inside
  your own work doesn't trigger anything — that's not public sharing.)

Suggested credit: *"Resource by Tom Cedoz — tomcedoz.com — licensed under CC BY-SA 4.0."*
The resources are general information, not legal advice.

## Structure

```
index.html              Home — Fig. 1 hero, featured tools, AI section, author strip
resources.html          The library (main feature), 32 tools in 4 groups (AI first)
resources/*.html        32 individual tools, each prints to 1–2 pages
insights.html           Articles and updates
insights/*.html         Full text of the Michigan Litigation Journal article
how-i-work.html         ~180 words on approach, one small grayscale photo
contact.html            Direct email (mailto) + firm bio link — no form
privacy.html            Privacy policy (honest, minimal — no cookies, no analytics)
assets/styles.css       The entire design system (screen + print)
assets/favicon.svg      Monogram favicon
assets/tom-cedoz.jpg    Optimized portrait (grayscale via CSS)
assets/og-default.png   1200×630 branded share image (Open Graph / Twitter)

robots.txt              Allows search + AI crawlers; points to the sitemap   ┐ generated
sitemap.xml             All 39 URLs                                          │ by
llms.txt                Markdown site index for LLMs / AI answer engines     ┘ seo_build.py

build_resources.py      Build-time: assembles generated resource pages + card grid
seo_build.py            Build-time: injects SEO/structured data + writes the 3 files above
build_deploy.py         Build-time: copies only the public deploy allowlist into dist/
check_content_review.py Internal QA: reports resources past legal-content review date
qa_static.py            Internal QA: validates links, metadata, JSON-LD, accessibility basics, deploy safety
check_external_links.py Internal QA: verifies public external links, with list-only mode for offline runs
archive_ad_record.py    Internal launch control: archives dist/ + manifest for ad-record retention
content_review.json     Internal QA: review owner + last/next review metadata
site_policy.json        Internal QA/source policy for robots, llms.txt, and license posture
privacy_inventory.json  Internal QA/source inventory for privacy-policy review
resources/_data/*.json  Source content for the 23 generated tools
seo/*.json              Workflow-authored SEO metadata (description, queries, internal FAQ notes) per page
```

## Build pipeline

Run both, in order, after changing any generated content:

```
python build_resources.py   # assemble resource pages + regenerate resources.html grid
python seo_build.py          # inject SEO/JSON-LD into every page; write robots/sitemap/llms
python check_content_review.py
python qa_static.py
python check_external_links.py --list-only
python build_deploy.py       # copy only public deploy files into dist/
python archive_ad_record.py --where https://tomcedoz.com/
```

`seo_build.py` is **idempotent** — it strips and re-injects a marked
`<!-- SEO:START … SEO:END -->` block in each `<head>`, so it is safe to re-run.
Always run it **after** `build_resources.py`, because the rebuild rewrites the 23
generated pages without the SEO block.

`build_resources.py`, `seo_build.py`, `resources/_data/`, and `seo/` are build-time
only. A static host should receive only the generated `dist/` directory created by
`build_deploy.py`.

## Deploying

Any static host works: GitHub Pages, Netlify, Cloudflare Pages, or your registrar's
simplest plan. Do **not** upload the whole workspace. It contains private working
files (`Writing/`, `review/`, the original full-resolution headshot, and local
tooling). Run:

```
python build_resources.py
python seo_build.py
python build_deploy.py
```

Then upload only `dist/`. The deploy builder uses an explicit allowlist: public
root HTML files, `assets/`, rendered `resources/*.html`, rendered
`insights/*.html`, `robots.txt`, `sitemap.xml`, and `llms.txt`. Make sure those
last three files land at the live site **root**.

After each public launch or material update, run `python archive_ad_record.py --where https://tomcedoz.com/`.
It writes an ignored `ad-records/` manifest and ZIP snapshot of `dist/`; retain
those records for at least two years after the last dissemination.

## Before going live

1. **Confirm the domain** — `seo_build.py` sets `DOMAIN = "https://tomcedoz.com"`
   (used for canonical URLs, sitemap, JSON-LD, and the share image URL). If the live
   domain differs, change it there and re-run `python seo_build.py`.
2. **Verify external links** — firm bio, blog posts, demo, GitHub, and the
   `mailto:` on the contact page are real but worth a click-through.
3. **After deploy** — submit `sitemap.xml` in Google Search Console and Bing Webmaster
   Tools, and validate a couple of pages with Google's Rich Results Test.

(The contact page is a direct `mailto:` to tom.cedoz@huschblackwell.com — no form, no
backend, nothing to configure.)

## SEO & AI discoverability

All of this is invisible to readers — it lives in `<head>` or root files, so it
doesn't touch the quiet design:

- **Per page**: canonical URL, robots directives, Open Graph + Twitter cards (with the
  branded share image), and schema.org **JSON-LD**.
- **Structured data**: `Person` (Tom, with `sameAs` to LinkedIn, the firm bio, and
  GitHub), `Organization`, and `WebSite`; `Article` + `BreadcrumbList` on every
  resource and the article; `CollectionPage` + `ItemList` (all 32 tools) on the
  library page. Hidden `FAQPage`, `Attorney`, `ProfessionalService`, and
  `LegalService` nodes are intentionally not emitted.
- **SEO metadata**: each content page's `seo/<slug>.json` holds an optimized meta
  description, real search queries, a one-line summary, and internal FAQ notes.
  The FAQ notes are not published as structured data unless the copy is made visible
  and routed through legal/content review.
- **Crawl/AI files**: `robots.txt` explicitly welcomes the major AI crawlers
  (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, …) based on
  `site_policy.json`; `sitemap.xml` lists every page; `llms.txt` is a markdown
  index of the whole library for LLMs. Confirm that crawler and license posture
  with legal, brand, and privacy stakeholders before launch.
- **Footer Privacy link**: `seo_build.py` also injects the site-wide `Privacy`
  footer link (depth-correct relative path) so every page links to `privacy.html`.

## Adding a resource

Add a JSON file under `resources/_data/`, register its slug in the `ORDER` map in
`build_resources.py`, then run the build pipeline above. (Hand-writing a page in
`resources/` also works; just run `seo_build.py` afterward so it gets the SEO block.)
Conventions that keep the library trustworthy:

- One topic, one or two printed pages. Cut until it fits.
- The `standfirst` says why the tool exists in two sentences, without selling.
- Voice: "Many in-house teams find…", "a pattern that has served clients well" —
  never "I'm the best because…".

## Design notes

- Palette: deep navy `#0a1f3f` (borrowed from the Litigation Journal's own ink),
  charcoal `#25272b`, white, and gray tints. Nothing else.
- The landing page's hero art ("Fig. 1") is an inline SVG drawn in hairlines — the
  record that exists before a complaint is filed, the thesis that most legal risk is
  decided early. It draws itself once on load; motion is gated behind
  `prefers-reduced-motion` and degrades to a static figure.
- Type: system serif for headlines and reading; system sans for labels, nav, and forms.
- Every resource page has a print stylesheet — "Print / save as PDF" produces a clean
  1–2 page document with a source line, print legal language, and without site chrome.
- Checklist checkboxes are real `<input type="checkbox">` elements: tickable on
  screen, empty squares on paper.
