#!/usr/bin/env python3
"""SEO + AI-answer-engine layer for tomcedoz.com.

Idempotent post-processor. Run AFTER build_resources.py:

    python build_resources.py && python seo_build.py

For every HTML page it injects (between <!-- SEO:START --> / <!-- SEO:END -->,
just before </head>): canonical URL, robots directives, Open Graph + Twitter
cards, and schema.org JSON-LD (Person, Article, BreadcrumbList, CollectionPage,
ItemList, etc.). It also refreshes each content page's meta description from the
workflow-authored data in seo/<key>.json, and (re)writes robots.txt, sitemap.xml,
and llms.txt. Invisible to readers; everything is in <head> or root files.
"""
import re, json, glob, os, html
from datetime import date

DOMAIN = "https://tomcedoz.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DATE = os.environ.get("SITE_BUILD_DATE", date.today().isoformat())
OG = DOMAIN + "/assets/og-default.png"

from build_resources import ORDER, GROUPS, EXISTING  # reuse the library structure

GROUP_TITLE = {k: html.unescape(t) for (k, gid, t, note) in GROUPS}
SLUG_GROUP = {s: k for k, slugs in ORDER.items() for s in slugs}

# ---- load workflow-authored SEO data -------------------------------------
SEO = {}
for p in glob.glob(os.path.join(ROOT, "seo", "*.json")):
    try:
        o = json.load(open(p, encoding="utf-8"))
        SEO[o["key"]] = o
    except Exception as e:
        print("  ! skipped", os.path.basename(p), e)

SITE_POLICY = {}
policy_path = os.path.join(ROOT, "site_policy.json")
if os.path.exists(policy_path):
    SITE_POLICY = json.load(open(policy_path, encoding="utf-8"))

CONTENT_REVIEW = {}
review_path = os.path.join(ROOT, "content_review.json")
if os.path.exists(review_path):
    CONTENT_REVIEW = json.load(open(review_path, encoding="utf-8")).get("items", {})

# ---- shared schema.org nodes ---------------------------------------------
PERSON_ID = DOMAIN + "/#tom"
ORG_ID = DOMAIN + "/#org"
SITE_ID = DOMAIN + "/#website"

PERSON = {
    "@type": "Person", "@id": PERSON_ID,
    "name": "Tom Cedoz", "alternateName": "Thomas J. Cedoz",
    "url": DOMAIN + "/", "image": DOMAIN + "/assets/tom-cedoz.jpg",
    "jobTitle": "Partner",
    "worksFor": {"@type": "Organization", "name": "Husch Blackwell LLP", "url": "https://www.huschblackwell.com/"},
    "homeLocation": {"@type": "Place", "name": "Metro Detroit, Michigan"},
    "knowsAbout": [
        "Labor and employment law", "Commercial litigation",
        "Fair Labor Standards Act collective actions",
        "Non-compete and restrictive covenant disputes", "Workplace investigations",
        "Reductions in force and the WARN Act", "Litigation holds and e-discovery",
        "Artificial intelligence legal risk and governance",
        "Employment discrimination defense", "Trade secret protection",
    ],
    "sameAs": [
        "https://www.linkedin.com/in/tomcedoz/",
        "https://www.huschblackwell.com/professionals/thomas-cedoz",
        "https://github.com/Tzodec1526",
    ],
}
ORG = {
    "@type": "Organization", "@id": ORG_ID, "name": "Tom Cedoz", "url": DOMAIN + "/",
    "logo": {"@type": "ImageObject", "url": OG, "width": 1200, "height": 630},
    "founder": {"@id": PERSON_ID},
}
WEBSITE = {
    "@type": "WebSite", "@id": SITE_ID, "url": DOMAIN + "/", "name": "Tom Cedoz",
    "description": "Practical resources for in-house counsel navigating employment risk and commercial disputes.",
    "publisher": {"@id": ORG_ID}, "inLanguage": "en-US",
}
AUDIENCE = {"@type": "Audience", "audienceType": "In-house counsel, general counsel, and HR leaders"}
PRINT_LEGAL = (
    '<div class="print-legal">'
    '<p>This site provides general information, not legal advice. Reading or using these materials, downloading resources, or contacting me through this site does not create an attorney-client relationship. Laws vary by jurisdiction and may change. Views are my own and not necessarily those of Husch Blackwell LLP or its clients. The choice of a lawyer is an important decision and should not be based solely upon advertisements.</p>'
    '</div>'
)

# ---- helpers --------------------------------------------------------------
def read(p): return open(p, encoding="utf-8").read()
def write(p, s): open(p, "w", encoding="utf-8").write(s)

def title_of(doc):
    m = re.search(r"<title>(.*?)</title>", doc, re.S)
    t = html.unescape(m.group(1).strip()) if m else "Tom Cedoz"
    return re.sub(r"\s*[—\-]\s*Tom Cedoz\s*$", "", t).strip()

def h1_of(doc):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else None

def desc_of(doc):
    m = re.search(r'<meta name="description" content="(.*?)">', doc, re.S)
    return html.unescape(m.group(1)) if m else ""

def attr(s):  # escape for a double-quoted HTML attribute
    return html.escape(s or "", quote=True)

def jsonld(nodes):
    payload = {"@context": "https://schema.org", "@graph": nodes}
    return ('<script type="application/ld+json">\n'
            + json.dumps(payload, ensure_ascii=False, indent=2) + "\n</script>")

def breadcrumb(trail):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
        for i, (n, u) in enumerate(trail)]}

def review_date(relpath):
    return CONTENT_REVIEW.get(relpath, {}).get("lastReviewed", BUILD_DATE)

def article_node(canonical, title, desc, section, date_modified):
    n = {
        "@type": "Article", "@id": canonical + "#article",
        "headline": title[:110], "name": title, "description": desc,
        "url": canonical, "mainEntityOfPage": canonical,
        "isPartOf": {"@id": SITE_ID}, "author": {"@id": PERSON_ID},
        "publisher": {"@id": ORG_ID}, "datePublished": "2026-06-10",
        "dateModified": date_modified, "inLanguage": "en-US",
        "image": OG, "articleSection": section, "audience": AUDIENCE,
        "isAccessibleForFree": True,
    }
    return n

# ---- the injectable <head> block -----------------------------------------
def build_block(canonical, og_type, og_title, desc, nodes):
    L = ["<!-- SEO:START (generated by seo_build.py — do not edit; re-run the script) -->",
         f'<link rel="canonical" href="{canonical}">',
         '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">',
         '<meta name="author" content="Tom Cedoz">',
         '<meta name="theme-color" content="#0a1f3f">']
    L += [f'<meta property="og:type" content="{og_type}">',
          '<meta property="og:site_name" content="Tom Cedoz">',
          '<meta property="og:locale" content="en_US">',
          f'<meta property="og:title" content="{attr(og_title)}">',
          f'<meta property="og:description" content="{attr(desc)}">',
          f'<meta property="og:url" content="{canonical}">',
          f'<meta property="og:image" content="{OG}">',
          '<meta property="og:image:width" content="1200">',
          '<meta property="og:image:height" content="630">',
          f'<meta property="og:image:alt" content="{attr("Tom Cedoz — practical resources for in-house counsel")}">',
          '<meta name="twitter:card" content="summary_large_image">',
          f'<meta name="twitter:title" content="{attr(og_title)}">',
          f'<meta name="twitter:description" content="{attr(desc)}">',
          f'<meta name="twitter:image" content="{OG}">',
          jsonld(nodes),
          "<!-- SEO:END -->"]
    return "\n".join(L)

BLOCK_RE = re.compile(r"\n?<!-- SEO:START.*?<!-- SEO:END -->\n?", re.S)

def normalize_inline_styles(doc):
    replacements = {
        'style="font-size:0.95rem"': 'class="foot-affiliation"',
        'style="font-family:var(--sans); font-size:0.8rem; color:#8b97ab"': 'class="foot-location"',
        'class="site-foot" style="margin-top:2rem"': 'class="site-foot foot-close"',
        'style="font-size:clamp(1.9rem,3.8vw,2.7rem)"': 'class="page-title"',
        'class="doc-head" style="margin-bottom:1.8rem"': 'class="doc-head doc-head-tight"',
        'class="doc-head" style="margin-bottom:2.4rem"': 'class="doc-head doc-head-loose"',
        'class="portrait" style="margin:0"': 'class="portrait"',
        'class="byline-strip rvs" style="margin-top:2.4rem"': 'class="byline-strip rvs byline-late"',
        'class="callout" style="max-width:var(--w-prose)"': 'class="callout callout-prose"',
        'class="hero" style="padding-bottom:3.2rem"': 'class="hero hero-library"',
        'class="hero" style="padding-bottom:3rem"': 'class="hero hero-insights"',
        'class="section" style="padding-top:4.2rem"': 'class="section section-recent"',
        'class="section" aria-label="The person behind it" style="padding-top:1rem"': 'class="section section-person" aria-label="The person behind it"',
        'style="font-family:var(--sans); font-size:0.85rem; color:var(--mist);"': 'class="article-note"',
        'style="font-family:var(--sans); font-size:0.85rem; color:var(--slate);"': 'class="article-note-slate"',
        'style="font-size:1.1rem"': 'class="article-mini-heading"',
        'style="border-left:2px solid var(--navy); margin:2rem 0; padding:0.4rem 0 0.4rem 1.4rem; font-size:1.25rem; line-height:1.5; color:var(--navy);"': 'class="article-pullquote"',
    }
    for old, new in replacements.items():
        doc = doc.replace(old, new)

    def steps_repl(match):
        start = int(match.group(1)) + 1
        return f'class="steps steps-start-{start}"'

    return re.sub(r'class="steps" style="counter-reset: step ([0-9]+);?"', steps_repl, doc)

def remove_third_party_fonts(doc):
    doc = re.sub(r'\n?<link rel="preconnect" href="https://fonts\.googleapis\.com">\n?', "\n", doc)
    doc = re.sub(r'\n?<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\n?', "\n", doc)
    doc = re.sub(r'\n?<link href="https://fonts\.googleapis\.com/css2\?[^"]+" rel="stylesheet">\n?', "\n", doc)
    return doc

def visible_breadcrumb(relpath):
    if relpath.startswith("resources/"):
        return '<nav class="crumbs" aria-label="Breadcrumb"><a href="../index.html">Home</a><span class="sep" aria-hidden="true">/</span><a href="../resources.html">Resources</a></nav>'
    if relpath.startswith("insights/"):
        return '<nav class="crumbs" aria-label="Breadcrumb"><a href="../index.html">Home</a><span class="sep" aria-hidden="true">/</span><a href="../insights.html">Insights</a></nav>'
    return ""

def apply_page(relpath, canonical, og_type, og_title, desc, nodes, new_desc=None):
    fp = os.path.join(ROOT, relpath)
    doc = read(fp)
    if new_desc:  # refresh the visible meta description
        esc = attr(new_desc)
        if re.search(r'<meta name="description" content=".*?">', doc, re.S):
            doc = re.sub(r'<meta name="description" content=".*?">',
                         f'<meta name="description" content="{esc}">', doc, count=1, flags=re.S)
    # site-wide footer Privacy + License links (idempotent), depth-correct relative path
    pfx = '../' if '/' in relpath else ''
    doc = re.sub(r'\n?<script src="(?:\.\./)?assets/site\.js"></script>\n?', "\n", doc)
    doc = re.sub(r'\n?<script>if \(\s*\'IntersectionObserver\'.*?</script>\n?', "\n", doc, flags=re.S)
    doc = re.sub(r'\n?<script>\s*\(function \(\) \{.*?document\.querySelectorAll\(\'.rvs\'\).*?\}\)\(\);\s*</script>\n?', "\n", doc, flags=re.S)
    doc = doc.replace(' class="btn-print" onclick="window.print()" type="button"', ' class="btn-print" type="button"')
    doc = normalize_inline_styles(doc)
    doc = remove_third_party_fonts(doc)
    doc = re.sub(r'\s*<nav class="crumbs" aria-label="Breadcrumb">.*?</nav>\s*', "\n\n      ", doc, flags=re.S)
    crumbs = visible_breadcrumb(relpath)
    if crumbs:
        doc = re.sub(
            r'(<div class="container">\s*)<header class="doc-head"',
            r'\1' + crumbs + '\n      <header class="doc-head"',
            doc,
            count=1
        )
    foot = ('<p><a href="' + pfx + 'privacy.html">Privacy</a> &middot; '
            '<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">License</a> &middot; tomcedoz.com</p>')
    doc = re.sub(r'<p>(?:<a[^>]*>Privacy</a> &middot; )?(?:<a[^>]*>License</a> &middot; )?tomcedoz\.com</p>', foot, doc, count=1)
    if 'class="print-note"' in doc:
        doc = re.sub(r'\s*<div class="print-legal">.*?</div>\s*', "\n", doc, flags=re.S)
        doc = doc.replace('<p class="print-note">', PRINT_LEGAL + "\n        <p class=\"print-note\">", 1)
    doc = BLOCK_RE.sub("\n", doc)  # strip any prior block (idempotent)
    block = build_block(canonical, og_type, og_title, desc, nodes)
    doc = doc.replace("</head>", block + f'\n<script src="{pfx}assets/site.js"></script>\n</head>', 1)
    write(fp, doc)

# ---- collect resource titles (for ItemList + breadcrumbs) ----------------
RES = {}  # slug -> {title, desc}
for slug in SLUG_GROUP:
    fp = os.path.join(ROOT, "resources", slug + ".html")
    if not os.path.exists(fp):
        print("  ! missing page for", slug); continue
    doc = read(fp)
    s = SEO.get(slug, {})
    RES[slug] = {"title": h1_of(doc) or title_of(doc),
                 "desc": s.get("metaDescription") or desc_of(doc)}

# ---- per resource page ----------------------------------------------------
n_pages = 0
for slug, info in RES.items():
    canonical = f"{DOMAIN}/resources/{slug}.html"
    s = SEO.get(slug, {})
    desc = info["desc"]
    section = GROUP_TITLE.get(SLUG_GROUP[slug], "Resources")
    rel = f"resources/{slug}.html"
    modified = review_date(rel)
    nodes = [article_node(canonical, info["title"], desc, section, modified),
             breadcrumb([("Home", DOMAIN + "/"), ("Resources", DOMAIN + "/resources.html"),
                         (info["title"], canonical)])]
    apply_page(rel, canonical, "article", info["title"], desc, nodes,
               new_desc=s.get("metaDescription"))
    n_pages += 1

# ---- the insight article --------------------------------------------------
art_rel = "insights/fixing-michigans-fragmented-e-filing.html"
art_canon = f"{DOMAIN}/{art_rel}"
adoc = read(os.path.join(ROOT, art_rel))
atitle = h1_of(adoc) or title_of(adoc)
s = SEO.get("insight-efiling", {})
adesc = s.get("metaDescription") or desc_of(adoc)
anode = {
    "@type": "Article", "@id": art_canon + "#article", "headline": atitle[:110],
    "name": atitle, "description": adesc, "url": art_canon, "mainEntityOfPage": art_canon,
    "isPartOf": {"@id": SITE_ID}, "author": {"@id": PERSON_ID}, "publisher": {"@id": ORG_ID},
    "datePublished": "2026-06-01", "dateModified": review_date(art_rel), "inLanguage": "en-US", "image": OG,
    "articleSection": "Technology & Practice",
    "isBasedOn": "https://github.com/Tzodec1526/MUEFS",
    "audience": AUDIENCE, "isAccessibleForFree": True,
}
anodes = [anode, breadcrumb([("Home", DOMAIN + "/"), ("Insights", DOMAIN + "/insights.html"), (atitle, art_canon)])]
apply_page(art_rel, art_canon, "article", atitle, adesc, anodes,
           new_desc=s.get("metaDescription"))
n_pages += 1

# ---- top-level pages ------------------------------------------------------
HOME_DESC = "Free checklists, frameworks, and quick-reference guides for in-house counsel and HR leaders navigating employment risk and commercial disputes. No email required."
home_nodes = [WEBSITE, PERSON, ORG]
apply_page("index.html", DOMAIN + "/", "website",
           "Practical resources for in-house counsel", HOME_DESC, home_nodes,
           new_desc=HOME_DESC)
n_pages += 1

# resources library: CollectionPage + ItemList of every tool
item_els, pos = [], 0
for gkey, slugs in ORDER.items():
    for slug in slugs:
        if slug in RES:
            pos += 1
            item_els.append({"@type": "ListItem", "position": pos,
                             "url": f"{DOMAIN}/resources/{slug}.html", "name": RES[slug]["title"]})
res_desc = "A curated, free library of checklists, frameworks, decision trees, and quick-reference guides for employment defense, commercial litigation, and AI legal risk."
res_nodes = [
    {"@type": "CollectionPage", "@id": DOMAIN + "/resources.html#page", "url": DOMAIN + "/resources.html",
     "name": "Resources — the library", "description": res_desc, "isPartOf": {"@id": SITE_ID},
     "about": [{"@type": "Thing", "name": GROUP_TITLE[k]} for k in ORDER], "audience": AUDIENCE},
    {"@type": "ItemList", "@id": DOMAIN + "/resources.html#tools", "name": "In-house counsel resource library",
     "numberOfItems": pos, "itemListOrder": "https://schema.org/ItemListOrderAscending",
     "itemListElement": item_els},
    breadcrumb([("Home", DOMAIN + "/"), ("Resources", DOMAIN + "/resources.html")]),
]
apply_page("resources.html", DOMAIN + "/resources.html", "website", "Resources — the library",
           res_desc, res_nodes, new_desc=res_desc)
n_pages += 1

# insights
ins_desc = "Articles and updates from Tom Cedoz on Michigan employment law, commercial litigation, legal technology, and AI in legal practice."
ins_nodes = [
    {"@type": "CollectionPage", "@id": DOMAIN + "/insights.html#page", "url": DOMAIN + "/insights.html",
     "name": "Insights", "description": ins_desc, "isPartOf": {"@id": SITE_ID}, "author": {"@id": PERSON_ID}},
    breadcrumb([("Home", DOMAIN + "/"), ("Insights", DOMAIN + "/insights.html")]),
]
apply_page("insights.html", DOMAIN + "/insights.html", "website", "Insights", ins_desc, ins_nodes,
           new_desc=ins_desc)
n_pages += 1

# how I work
hiw_desc = "How Tom Cedoz approaches employment and commercial litigation: learn the business first, give clear recommendations, and treat the budget as part of the case."
hiw_nodes = [
    {"@type": "AboutPage", "@id": DOMAIN + "/how-i-work.html#page", "url": DOMAIN + "/how-i-work.html",
     "name": "How I Work", "description": hiw_desc, "isPartOf": {"@id": SITE_ID}, "mainEntity": {"@id": PERSON_ID}},
    PERSON,
    breadcrumb([("Home", DOMAIN + "/"), ("How I Work", DOMAIN + "/how-i-work.html")]),
]
apply_page("how-i-work.html", DOMAIN + "/how-i-work.html", "website", "How I Work", hiw_desc, hiw_nodes,
           new_desc=hiw_desc)
n_pages += 1

# contact
con_desc = "Contact Tom Cedoz — professional inquiries, questions about the resources, or suggestions for tools the library is missing."
con_nodes = [
    {"@type": "ContactPage", "@id": DOMAIN + "/contact.html#page", "url": DOMAIN + "/contact.html",
     "name": "Contact", "description": con_desc, "isPartOf": {"@id": SITE_ID}, "mainEntity": {"@id": PERSON_ID}},
    breadcrumb([("Home", DOMAIN + "/"), ("Contact", DOMAIN + "/contact.html")]),
]
apply_page("contact.html", DOMAIN + "/contact.html", "website", "Contact", con_desc, con_nodes,
           new_desc=con_desc)
n_pages += 1

# privacy policy
priv_desc = "How tomcedoz.com handles data: no tracking cookies, no analytics that identify you, nothing sold or shared for marketing. The full, plain-English account."
priv_nodes = [
    {"@type": "WebPage", "@id": DOMAIN + "/privacy.html#page", "url": DOMAIN + "/privacy.html",
     "name": "Privacy Policy", "description": priv_desc, "isPartOf": {"@id": SITE_ID}, "about": {"@id": ORG_ID}},
    breadcrumb([("Home", DOMAIN + "/"), ("Privacy Policy", DOMAIN + "/privacy.html")]),
]
apply_page("privacy.html", DOMAIN + "/privacy.html", "website", "Privacy Policy", priv_desc, priv_nodes,
           new_desc=priv_desc)
n_pages += 1

# ---- robots.txt -----------------------------------------------------------
crawler_policy = SITE_POLICY.get("crawlerPolicy", {})
ai_bots = crawler_policy.get("aiBots", [])
default_directive = "Allow: /" if crawler_policy.get("defaultAccess", "allow") == "allow" else "Disallow: /"
ai_directive = "Allow: /" if crawler_policy.get("aiCrawlerAccess", "allow") == "allow" else "Disallow: /"
robots = ["# tomcedoz.com - generated from site_policy.json.",
          f"# Policy review status: {SITE_POLICY.get('reviewStatus', 'unspecified')}",
          "User-agent: *", default_directive, ""]
for b in ai_bots:
    robots += [f"User-agent: {b}", ai_directive, ""]
robots += [f"Sitemap: {DOMAIN}/sitemap.xml", ""]
write(os.path.join(ROOT, "robots.txt"), "\n".join(robots))

# ---- sitemap.xml ----------------------------------------------------------
def url_entry(loc, pri, freq="monthly", lastmod=BUILD_DATE):
    return (f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>")
urls = [url_entry(DOMAIN + "/", "1.0", "weekly"),
        url_entry(DOMAIN + "/resources.html", "0.9", "weekly"),
        url_entry(DOMAIN + "/insights.html", "0.7"),
        url_entry(DOMAIN + "/how-i-work.html", "0.5"),
        url_entry(DOMAIN + "/contact.html", "0.5"),
        url_entry(DOMAIN + "/privacy.html", "0.3"),
        url_entry(art_canon, "0.7", lastmod=review_date(art_rel))]
for gkey, slugs in ORDER.items():
    for slug in slugs:
        if slug in RES:
            urls.append(url_entry(f"{DOMAIN}/resources/{slug}.html", "0.8", lastmod=review_date(f"resources/{slug}.html")))
sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
write(os.path.join(ROOT, "sitemap.xml"), sitemap)

# ---- llms.txt (AI/LLM site index) ----------------------------------------
def summ(slug):
    return SEO.get(slug, {}).get("summary") or RES[slug]["desc"]
ll = ["# Tom Cedoz — Practical resources for in-house counsel", "",
      "> A quiet, free library of checklists, frameworks, decision trees, and quick-reference "
      "guides for in-house counsel, general counsel, and HR leaders navigating employment risk "
      "and commercial disputes. Written and maintained by Tom Cedoz, a litigator at Husch "
      "Blackwell (labor & employment defense and commercial litigation). Every resource is free, "
      "printable, and requires no email. This file helps AI systems cite the library accurately.", ""]
for gkey, gid, gtitle, note in GROUPS:
    ll.append(f"## {html.unescape(gtitle)}")
    ll.append("")
    for slug in ORDER[gkey]:
        if slug in RES:
            ll.append(f"- [{RES[slug]['title']}]({DOMAIN}/resources/{slug}.html): {summ(slug)}")
    ll.append("")
ll += ["## Insights", "",
       f"- [{atitle}]({art_canon}): {SEO.get('insight-efiling', {}).get('summary', adesc)}",
       f"- [All insights]({DOMAIN}/insights.html): articles on employment law, commercial litigation, and AI in legal practice.", "",
       "## About", "",
       f"- [How I Work]({DOMAIN}/how-i-work.html): Tom Cedoz's client-immersion approach to litigation.",
       f"- [Contact]({DOMAIN}/contact.html): professional inquiries and resource suggestions.",
       "- Tom Cedoz practices with Husch Blackwell LLP (Metro Detroit, Michigan). Firm bio: "
       "https://www.huschblackwell.com/professionals/thomas-cedoz", ""]
write(os.path.join(ROOT, "llms.txt"), "\n".join(ll))

print(f"SEO applied to {n_pages} pages.")
print(f"SEO data found for {len(SEO)} pages; ItemList has {pos} tools.")
print("Wrote robots.txt, sitemap.xml ({} urls), llms.txt.".format(len(urls)))
