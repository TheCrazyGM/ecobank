"""Content loading + JSON-LD helpers for the aliados blueprint.

Each partner is a folder under content/. Inside it:
  - partner.md   -> the pillar page (config in frontmatter + intro body)
  - <slug>.md    -> one species (spoke) page each

Frontmatter drives <title>, meta description, and structured data;
the Markdown body is the visible content.
"""
from pathlib import Path
from functools import lru_cache
import frontmatter
import markdown

CONTENT = Path(__file__).parent / "content"
STATIC = Path(__file__).parent / "static"
MD_EXTENSIONS = ["extra", "sane_lists", "smarty"]
PLACEHOLDER_IMAGE = "/aliados/static/img/placeholder.jpg"


def _resolve_image(image: str | None) -> str | None:
    """Fall back to a branded placeholder when the declared photo isn't on disk yet.

    Keeps frontmatter pointing at the real intended path, so dropping the
    actual file in later just works with no content edits.
    """
    if not image:
        return PLACEHOLDER_IMAGE
    if image.startswith("http"):
        return image
    local_path = STATIC / image.removeprefix("/aliados/static/").lstrip("/")
    return image if local_path.exists() else PLACEHOLDER_IMAGE


def _load(path: Path) -> dict:
    post = frontmatter.load(path)
    data = dict(post.metadata)
    if "image" in data:
        data["image"] = _resolve_image(data["image"])
    data["body_html"] = markdown.markdown(post.content, extensions=MD_EXTENSIONS)
    return data


@lru_cache(maxsize=None)
def load_partner(slug: str):
    f = CONTENT / slug / "partner.md"
    if not f.exists():
        return None
    d = _load(f)
    d["slug"] = slug
    return d


@lru_cache(maxsize=None)
def load_species(partner: str, slug: str):
    f = CONTENT / partner / f"{slug}.md"
    if not f.exists() or slug == "partner":
        return None
    d = _load(f)
    d["slug"] = slug
    d["partner"] = partner
    return d


def list_partners():
    if not CONTENT.exists():
        return []
    return [load_partner(p.name) for p in sorted(CONTENT.iterdir()) if p.is_dir()]


def list_species(partner: str):
    d = CONTENT / partner
    if not d.exists():
        return []
    items = [load_species(partner, f.stem) for f in d.glob("*.md") if f.stem != "partner"]
    items = [s for s in items if s]
    # heroes first, then alphabetical by scientific name
    return sorted(items, key=lambda s: (not s.get("hero"), s.get("scientific_name", "")))


# --------------------------------------------------------------------------
# schema.org / JSON-LD
# --------------------------------------------------------------------------
def _abs(url_or_path: str, site_root: str):
    if not url_or_path:
        return None
    if url_or_path.startswith("http"):
        return url_or_path
    return site_root.rstrip("/") + "/" + url_or_path.lstrip("/")


def product_graph(s, partner, page_url, site_root):
    props = [
        {"@type": "PropertyValue", "name": "Nombre científico", "value": s.get("scientific_name")},
        {"@type": "PropertyValue", "name": "Familia", "value": s.get("family")},
    ]
    if s.get("conservation"):
        props.append({"@type": "PropertyValue", "name": "Estado de conservación", "value": s["conservation"]})
    if s.get("cites"):
        props.append({"@type": "PropertyValue", "name": "CITES", "value": s["cites"]})

    offer = {
        "@type": "Offer",
        "availability": "https://schema.org/" + s.get("availability", "MadeToOrder"),
        "priceCurrency": "COP",
        "url": page_url,
        "seller": {"@type": "LocalBusiness", "name": partner.get("partner_name", ""), "areaServed": "CO"},
    }
    if s.get("price"):
        offer["price"] = str(s["price"])

    product = {
        "@type": "Product",
        "name": s.get("meta_title") or f"{s.get('title')} ({s.get('scientific_name')})",
        "alternateName": s.get("common_names", []),
        "description": s.get("meta_description", ""),
        "category": "Árboles nativos",
        "brand": {"@type": "Brand", "name": partner.get("partner_name", "")},
        "additionalProperty": props,
        "offers": offer,
    }
    img = _abs(s.get("image"), site_root)
    if img:
        product["image"] = img

    return {
        "@context": "https://schema.org",
        "@graph": [product, _breadcrumb(s, partner, site_root)],
    }


def collection_graph(partner, species, page_url, site_root):
    items = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "name": f"{s.get('title')} ({s.get('scientific_name')})",
            "url": _abs(f"aliados/{partner['slug']}/{s['slug']}", site_root),
        }
        for i, s in enumerate(species)
    ]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": partner.get("meta_title") or partner.get("pillar_title"),
                "description": partner.get("meta_description", ""),
                "url": page_url,
                "mainEntity": {"@type": "ItemList", "itemListElement": items},
            },
            {
                "@type": "LocalBusiness",
                "name": partner.get("partner_name", ""),
                "description": partner.get("meta_description", ""),
                "areaServed": "CO",
                "url": page_url,
                "telephone": partner.get("whatsapp", ""),
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Inicio", "item": site_root},
                    {"@type": "ListItem", "position": 2, "name": partner.get("pillar_title"), "item": page_url},
                ],
            },
        ],
    }


def _breadcrumb(s, partner, site_root):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": site_root},
            {"@type": "ListItem", "position": 2, "name": partner.get("pillar_title"),
             "item": _abs(f"aliados/{partner['slug']}/", site_root)},
            {"@type": "ListItem", "position": 3, "name": s.get("title"),
             "item": _abs(f"aliados/{partner['slug']}/{s['slug']}", site_root)},
        ],
    }
