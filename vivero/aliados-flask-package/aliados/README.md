# Aliados — native-species SEO pages (Flask blueprint)

A self-contained Flask blueprint that serves partner ("aliados") landing
pages under `/aliados/<pillar-slug>/[<species-slug>]`, driven entirely by
Markdown + frontmatter. No database. Isolated from the rest of your site.

Verified working (all routes 200, valid JSON-LD, sitemap, 404s on unknown).

## Install

```bash
pip install -r aliados/requirements.txt
```

## Integrate into your existing Flask app

Two lines:

```python
from aliados import aliados
app.register_blueprint(aliados)
```

That's it. The blueprint carries its own templates, static files, and content.

Preview locally with the included example:

```bash
python example_app.py
# http://127.0.0.1:8010/aliados/vivero-especies-nativas-colombia/
```

## URL scheme

```
/aliados/                                → index of partners
/aliados/<pillar-slug>/                  → pillar (hub) page
/aliados/<pillar-slug>/<species-slug>    → species (spoke) page
/aliados/sitemap.xml                     → sitemap (submit in Search Console)
```

The middle slug is an SEO lever — make it keyword-rich, e.g.
`vivero-especies-nativas-colombia`.

## Add a species

Drop a new `<slug>.md` into the partner folder
(`aliados/content/vivero-especies-nativas-colombia/`) with frontmatter:

```yaml
---
title: "Guamo"
scientific_name: "Inga edulis"
common_names: [guamo, guama, guaba]        # → JSON-LD alternateName
family: "Fabaceae"
cluster: "fijadoras-nitrogeno"             # must match a cluster id in partner.md
hero: true                                 # shows in the insignia band
teaser: "Short card blurb."
conservation: null                         # or "En Peligro Crítico (CR)" → badge
cites: null                                # or "Apéndice II" → badge
availability: "MadeToOrder"
image: "/aliados/static/img/guamo.jpg"
meta_title: "..."
meta_description: "..."
---
Markdown body (the visible ficha)...
```

Restart the app to pick up new/edited content (content is cached in memory).

## Rebrand

Override the CSS tokens at the top of `aliados/static/aliados/aliados.css`
(`--paper`, `--canopy`, `--leaf`, fonts…) to match ecobankdevelopment.com.
The starter palette is grounded in the Andean cloud forest; swap freely.

## robots.txt

Add (at site level) a line pointing crawlers to the sitemap:

```
Sitemap: https://ecobankdevelopment.com/aliados/sitemap.xml
```

## Optional: freeze to static HTML

If you'd rather serve static files (max performance, or to drop into a
non-Flask site), add `Frozen-Flask` and a small `freeze.py` — see the
integration plan doc for the snippet.

## Included content

- `partner.md` — pillar (fill in `[Nombre del vivero]`, WhatsApp number).
- `chachafruto.md`, `guamo.md` — the two N-fixing hero species.
- `comino-crespo.md` — conservation flagship (shows the CR badge).

Twelve more species to add; confirm the ⚠ common names against
biovirtual.unal.edu.co/nombrescomunes first.
```
