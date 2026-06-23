#!/usr/bin/env python3
"""Assemble resource pages from resources/_data/*.json and regenerate resources.html.

Content (the JSON) is authored by the workflow; presentation (this template) is
deterministic so every page matches the existing hand-built pages exactly.
"""
import json, os, sys, glob, re, html as _html

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "resources", "_data")
OUT  = os.path.join(ROOT, "resources")

PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{metaTitle}</title>
<meta name="description" content="{metaDescription}">
<link rel="icon" type="image/svg+xml" href="../assets/favicon.svg">
<link rel="stylesheet" href="../assets/styles.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-head">
  <div class="container head-row">
    <a class="wordmark" href="../index.html">Tom&nbsp;Cedoz</a>
    <nav class="site-nav" aria-label="Site">
      <a href="../resources.html" aria-current="page">Resources</a>
      <a href="../insights.html">Insights</a>
      <a href="../how-i-work.html">How I Work</a>
      <a href="../contact.html">Contact</a>
    </nav>
  </div>
</header>

<main id="main">
  <article class="doc">
    <div class="container">

      <nav class="crumbs" aria-label="Breadcrumb"><a href="../index.html">Home</a><span class="sep" aria-hidden="true">/</span><a href="../resources.html">Resources</a></nav>
      <header class="doc-head">
        <p class="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p class="standfirst">{standfirst}</p>
        <div class="doc-meta">
          <span>{m0}</span><span class="dot">&middot;</span>
          <span>{m1}</span><span class="dot">&middot;</span>
          <span>{m2}</span>
          <button class="btn-print" type="button">Print / save as PDF</button>
        </div>
      </header>

      <div class="prose">

{body}

      </div>

      <footer class="doc-foot">
        <p class="related">Related: {related}</p>
        <p class="backlink"><a href="../resources.html">&larr; All resources</a></p>
        <div class="print-legal"><p>This site provides general information, not legal advice. Reading or using these materials, downloading resources, or contacting me through this site does not create an attorney-client relationship. Laws vary by jurisdiction and may change. Views are my own and not necessarily those of Husch Blackwell LLP or its clients. The choice of a lawyer is an important decision and should not be based solely upon advertisements.</p></div>
        <p class="print-note">tomcedoz.com &middot; {plain} &middot; Updated June 2026 &middot; General information, not legal advice &middot; &copy; 2026 Tom Cedoz</p>
      </footer>

    </div>
  </article>
</main>

<footer class="site-foot">
  <div class="container foot-grid">
    <div>
      <p class="foot-name">Tom Cedoz</p>
      <p class="foot-affiliation">I practice with <a href="https://www.huschblackwell.com/professionals/thomas-cedoz" rel="noopener">Husch Blackwell</a>.</p>
      <p class="foot-location">Metro Detroit, Michigan</p>
    </div>
    <nav class="foot-nav" aria-label="Footer">
      <a href="../resources.html">Resources</a>
      <a href="../insights.html">Insights</a>
      <a href="../how-i-work.html">How I Work</a>
      <a href="../contact.html">Contact</a>
    </nav>
    <div class="foot-legal">
      <p>This site provides general information, not legal advice. Reading or using these materials, downloading resources, or contacting me through this site does not create an attorney-client relationship. Laws vary by jurisdiction and may change. Views are my own and not necessarily those of Husch Blackwell LLP or its clients. The choice of a lawyer is an important decision and should not be based solely upon advertisements.</p>
    </div>
  </div>
  <div class="container foot-bottom">
    <p>&copy; 2026 Tom Cedoz</p>
    <p>tomcedoz.com</p>
  </div>
</footer>

</body>
</html>
'''

# ----- existing nine (verbatim card data from the hand-built page) -----
EXISTING = {
 "eeoc-charge-first-72-hours": ("Checklist &middot; Employment","Responding to an EEOC Charge: The First 72 Hours","Deadlines, the litigation hold, carrier notice, decision-maker identification, and the retaliation briefing — sequenced for the first three days.","14 items &middot; 2 pages"),
 "termination-risk-review": ("Framework &middot; Employment","Termination Risk Review: Nine Questions Before You Decide","The pre-termination review many in-house teams run from memory, written down: the reason, the file, consistency, timing, and the mechanics that create claims on their own.","9 questions &middot; 1 page"),
 "fmla-ada-decision-tree": ("Decision tree &middot; Employment","The FMLA&ndash;ADA Interplay: A Decision Tree","Where leave law actually gets dangerous: what happens when FMLA runs out, when it never applied, and why automatic termination at week twelve buys ADA claims.","1 tree + 5 steps &middot; 2 pages"),
 "workplace-investigations-guide": ("Quick reference &middot; Employment","Workplace Investigations: A Quick Reference","Intake to closing memo: choosing the investigator (and what that does to privilege), interim measures, interview order, credibility factors, and the file you should end with.","7 sections &middot; 2 pages"),
 "rif-compliance-checklist": ("Checklist &middot; Employment","Reduction in Force: A Compliance Checklist","Selection criteria, adverse-impact review under privilege, WARN math, OWBPA release requirements, and the communications plan — in the order they need to happen.","18 items &middot; 2 pages"),
 "demand-letter-triage": ("Framework &middot; Commercial","Demand Letter Triage: The First Week","An eight-step sequence for any serious demand: deadlines, preservation, insurance notice, the contract itself, and choosing a response posture on purpose.","8 steps &middot; 2 pages"),
 "early-case-assessment": ("Framework &middot; Commercial","Early Case Assessment: Twelve Questions Before You Litigate","The questions that decide whether a case is worth bringing or worth settling — exposure, documents, witnesses, forum, fees, counterclaims, and the exit ramps.","12 questions &middot; 2 pages"),
 "contract-dispute-pre-suit-checklist": ("Checklist &middot; Commercial","Contract Disputes: The Pre-Suit Checklist","Conditions precedent hiding in the contract — notice and cure, ADR escalators, forum clauses, shortened limitations — plus the performance question: keep going or stop?","16 items &middot; 2 pages"),
 "litigation-hold-checklist": ("Checklist &middot; Cross-practice","Litigation Hold: Trigger to Release","When the duty to preserve attaches, what a defensible hold covers, the sources teams forget — texts, Slack, CCTV loops, departing employees — and how holds end.","full lifecycle &middot; 2 pages"),
}

ORDER = {
 "ai": ["ai-hype-vs-reality","ai-hiring-employment","ai-employee-monitoring","ai-use-policy",
   "ai-governance-inventory","ai-vendor-contract","ai-litigation-verification"],
 "employment": ["eeoc-charge-first-72-hours","termination-risk-review","fmla-ada-decision-tree",
   "ada-interactive-process","workplace-investigations-guide","rif-compliance-checklist","flsa-exemption-audit",
   "independent-contractor-classification","restrictive-covenant-review","departing-employee-protection",
   "hiring-from-competitor","severance-release-checklist"],
 "commercial": ["demand-letter-triage","early-case-assessment","contract-dispute-pre-suit-checklist",
   "contract-risk-review","nda-triage","indemnification-limitation-liability","insurance-tender"],
 "cross": ["litigation-hold-checklist","third-party-subpoena-response","privilege-in-house",
   "corporate-witness-30b6","records-retention","data-incident-first-48-hours"],
}

GROUPS = [
 ("ai","g-ai","AI &amp; emerging risk",
  "Adopting AI creates new legal exposure &mdash; in hiring, contracts, governance, and the courtroom. These tools separate what AI is genuinely good at from what you&rsquo;re being sold, and help you put the guardrails in before something goes wrong, not after."),
 ("employment","g-employment","Labor &amp; employment defense",
  "For the moments HR escalates: a charge, a complaint, a leave request that has outgrown the policy, a termination that doesn&rsquo;t feel routine, a workforce reduction on a deadline."),
 ("commercial","g-commercial","Commercial litigation",
  "For disputes between businesses: the demand letter, the contract everyone suddenly reads closely, and the decision — made deliberately or by drift — about whether to fight."),
 ("cross","g-cross","Either way, both ways",
  "The tools that apply the moment any dispute becomes foreseeable, employment or commercial."),
]

def load_new():
    data = {}
    for p in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        try:
            obj = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print("  ! JSON parse FAILED:", os.path.basename(p), "->", e); continue
        data[obj["slug"]] = obj
    return data

def render_pages(newdata):
    n = 0
    for slug, o in newdata.items():
        mi = o["docMetaItems"]
        html = PAGE.format(
            metaTitle=o["metaTitle"], metaDescription=o["metaDescription"],
            eyebrow=o["eyebrow"], title=o["title"], standfirst=o["standfirst"],
            m0=mi[0], m1=mi[1], m2=mi[2], body=o["bodyHtml"].strip(),
            related=o["relatedHtml"], plain=o["title"],
        )
        open(os.path.join(OUT, slug + ".html"), "w", encoding="utf-8").write(html)
        n += 1
    return n

def _searchtext(*parts):
    """Plain lowercase word string for client-side filtering (no tags/entities)."""
    s = " ".join(parts)
    s = re.sub(r"<[^>]+>", " ", s)               # strip tags
    s = _html.unescape(s)                         # decode &middot; &mdash; &rsquo; etc.
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())     # words only
    return " ".join(s.split())

def card(slug, newdata, group):
    if slug in EXISTING:
        t, title, desc, meta = EXISTING[slug]
    else:
        o = newdata[slug]; t, title, desc, meta = o["cardType"], o["cardTitle"], o["cardDesc"], o["cardMeta"]
    return ('          <article class="res-card" data-group="%s" data-text="%s">\n'
            '            <p class="type">%s</p>\n'
            '            <h3><a href="resources/%s.html">%s</a></h3>\n'
            '            <p class="desc">%s</p>\n'
            '            <p class="meta"><span>%s</span><span class="arrow" aria-hidden="true">&rarr;</span></p>\n'
            '          </article>') % (group, _searchtext(title, desc, t), t, slug, title, desc, meta)

CAT_LABELS = [("all", "All"), ("ai", "AI"), ("employment", "Employment"),
              ("commercial", "Commercial"), ("cross", "Cross-practice")]

def render_section(newdata):
    total = sum(len(v) for v in ORDER.values())
    blocks = []
    for key, gid, gtitle, gnote in GROUPS:
        cards = "\n\n".join(card(s, newdata, key) for s in ORDER[key])
        blocks.append(
            '      <div class="res-group">\n'
            '        <div class="section-head">\n'
            '          <h2 id="%s">%s</h2>\n'
            '        </div>\n'
            '        <p class="groupnote">%s</p>\n'
            '        <div class="res-grid">\n\n%s\n\n        </div>\n'
            '      </div>' % (gid, gtitle, gnote, cards))
    catbtns = "\n".join(
        '          <button type="button" class="res-cat%s" data-cat="%s" aria-pressed="%s">%s</button>'
        % (" is-active" if k == "all" else "", k, "true" if k == "all" else "false", lbl)
        for k, lbl in CAT_LABELS)
    filt = (
        '      <div class="res-filter" role="search" data-total="%d">\n'
        '        <div class="res-filter-row">\n'
        '          <label class="res-filter-field">\n'
        '            <span class="res-filter-label">Search</span>\n'
        '            <input type="search" id="res-q" placeholder="Search by name or topic…" autocomplete="off" spellcheck="false">\n'
        '          </label>\n'
        '          <div class="res-cats" role="group" aria-label="Filter by category">\n%s\n          </div>\n'
        '        </div>\n'
        '        <p class="res-count" id="res-count" role="status" aria-live="polite"></p>\n'
        '      </div>' % (total, catbtns))
    noresults = ('      <p class="res-noresults" id="res-noresults" hidden>Nothing matches that search. '
                 '<button type="button" class="res-reset">Clear filters</button></p>')
    callout = ('      <div class="callout callout-prose">\n'
               '        <span class="callout-label">How to use these</span>\n'
               '        <p>Use them in your own work freely — print them, drop them into your playbooks, adapt them to your policies. If you republish or redistribute them, the license (<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">CC&nbsp;BY-SA&nbsp;4.0</a>) asks only that you keep the credit and share under the same terms. They describe patterns, not your facts: state law varies more than most teams expect, and several of these areas (non-competes, leave laws, final-pay rules) are moving targets. When a real matter is on the table, run the specifics past your counsel.</p>\n'
               '      </div>')
    return ('  <section class="section library-sections" aria-labelledby="' + GROUPS[0][1] + '">\n'
            '    <div class="container">\n\n' +
            filt + "\n\n" + noresults + "\n\n" +
            "\n\n".join(blocks) + "\n\n" + callout +
            '\n\n    </div>\n  </section>')

def patch_index(newdata):
    """Update the home page 'Start here' grid + the count line, if present."""
    pass  # left unchanged by design; home stays a curated 4

def main():
    newdata = load_new()
    print("Loaded %d new resources from JSON." % len(newdata))
    missing = [s for g in ORDER.values() for s in g if s not in EXISTING and s not in newdata]
    if missing:
        print("  ! Missing JSON for:", ", ".join(missing))
    pages = render_pages(newdata)
    print("Wrote %d resource pages." % pages)

    rp = os.path.join(ROOT, "resources.html")
    txt = open(rp, encoding="utf-8").read()
    try:
        a = txt.index('  <section class="section library-sections"')
    except ValueError:
        a = txt.index('  <section class="section" aria-labelledby="g-employment">')
    b = txt.index('</main>')
    new_txt = txt[:a] + render_section(newdata) + "\n\n" + txt[b:]
    open(rp, "w", encoding="utf-8").write(new_txt)
    total = sum(len(v) for v in ORDER.values())
    print("Regenerated resources.html with %d cards across %d groups." % (total, len(GROUPS)))

if __name__ == "__main__":
    main()
