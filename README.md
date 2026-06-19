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


