# Plan de integración — Páginas SEO de aliados en Flask

Objetivo: servir las páginas de especies nativas del vivero (y de otros aliados
en el futuro) bajo `ecobankdevelopment.com/aliados/<pillar-slug>/<species>`,
**independientes de la estructura del sitio actual**, con SEO técnico completo.

---

## 1. Arquitectura en una frase

Un **Blueprint de Flask autocontenido**, montado en `/aliados`, que renderiza
páginas a partir de **archivos Markdown con frontmatter** (sin base de datos).
Tu contenido queda versionado en git; agregar una especie = agregar un `.md`.

Ventajas: aislado del resto del sitio, cero acoplamiento, git-friendly, y tus
borradores actuales (`comino-crespo-pagina-modelo.md`, la pilar) se convierten
directamente en contenido.

---

## 2. La única bifurcación que define el despliegue

**¿El sitio actual de ecobankdevelopment.com ya es Flask, o es otra cosa
(WordPress, estático, etc.)?**

- **Ya es Flask** → registras el blueprint en la app existente. Una línea:
  `app.register_blueprint(aliados)`. Cero fricción.
- **Es otra cosa** → corres esta como **app Flask independiente** y enrutas
  `/aliados/` por reverse proxy (nginx), o **congelas a HTML estático**
  (Frozen-Flask, §9) y dejas la carpeta `/aliados/` dentro del sitio actual.

El plan de abajo funciona igual en ambos casos: el blueprint es el mismo; solo
cambia cómo se monta (§10).

---

## 3. Esquema de URLs

```
/aliados/                                  → índice de aliados (opcional)
/aliados/<pillar-slug>/                     → página pilar del aliado
/aliados/<pillar-slug>/<species-slug>       → página de especie (spoke)
/aliados/sitemap.xml                        → sitemap de esta sección
/aliados/robots.txt                         → (o a nivel de sitio)
```

Ejemplo real:
```
/aliados/vivero-especies-nativas-colombia/
/aliados/vivero-especies-nativas-colombia/chachafruto
/aliados/vivero-especies-nativas-colombia/comino-crespo
```

El `<pillar-slug>` es un lever SEO: hazlo rico en palabras clave.

---

## 4. Estructura del repositorio

```
aliados/
├── __init__.py            # define el Blueprint
├── routes.py              # rutas: index, pilar, especie, sitemap
├── content.py             # loader Markdown + frontmatter (+ caché)
├── templates/aliados/
│   ├── base.html          # layout propio, independiente del sitio actual
│   ├── index.html
│   ├── pillar.html
│   ├── species.html
│   ├── _jsonld.html       # macro de datos estructurados
│   └── sitemap.xml
├── static/aliados/        # CSS/JS/imágenes propios
└── content/
    └── vivero-especies-nativas-colombia/
        ├── partner.md     # config + cuerpo de la pilar
        ├── chachafruto.md
        ├── guamo.md
        ├── comino-crespo.md
        └── ... (14 especies)
```

---

## 5. Modelo de contenido (frontmatter)

Cada especie es un `.md`. El frontmatter alimenta `<title>`, meta, y JSON-LD;
el cuerpo Markdown es el contenido visible. Mapea 1:1 con los borradores ya hechos.

```yaml
---
scientific_name: Erythrina edulis
common_names: [chachafruto, balú, basul, poroto, sachaporoto, frijol nupe]
family: Fabaceae
cluster: fijadoras-nitrogeno      # agrupa en la pilar
hero: true                        # aparece en la banda insignia
conservation: null                # o "En Peligro Crítico (CR)"
cites: null                       # o "Apéndice II"
uses: [agroforestería, alimento, fija nitrógeno]
availability: MadeToOrder         # → schema.org/MadeToOrder
price: null
image: /aliados/static/img/chachafruto.jpg
meta_title: "Chachafruto (Erythrina edulis) — árbol nativo por encargo"
meta_description: "Chachafruto: leguminosa andina de semilla comestible, fija nitrógeno. Plántulas por rescate, disponibles por encargo (tanda a la medida)."
---

Cuerpo en Markdown (la ficha que ya redactamos)...
```

`partner.md` guarda la config de la pilar (nombre del vivero, título, intro,
teléfono/WhatsApp) más el cuerpo Markdown de la pilar.

---

## 6. Código de referencia

### `aliados/__init__.py`
```python
from flask import Blueprint

aliados = Blueprint(
    "aliados", __name__,
    url_prefix="/aliados",
    template_folder="templates",
    static_folder="static",
    static_url_path="/aliados/static",
)

from . import routes  # noqa: E402  (registra las rutas)
```

### `aliados/content.py`
```python
from pathlib import Path
from functools import lru_cache
import frontmatter
import markdown

CONTENT = Path(__file__).parent / "content"
MD_EXT = ["extra", "sane_lists", "smarty"]

def _load(path: Path):
    post = frontmatter.load(path)
    data = dict(post.metadata)
    data["body_html"] = markdown.markdown(post.content, extensions=MD_EXT)
    return data

@lru_cache(maxsize=None)
def load_partner(slug: str):
    f = CONTENT / slug / "partner.md"
    if not f.exists():
        return None
    d = _load(f); d["slug"] = slug
    return d

@lru_cache(maxsize=None)
def load_species(partner: str, slug: str):
    f = CONTENT / partner / f"{slug}.md"
    if not f.exists():
        return None
    d = _load(f); d["slug"] = slug; d["partner"] = partner
    return d

def list_partners():
    return [load_partner(p.name) for p in CONTENT.iterdir() if p.is_dir()]

def list_species(partner: str):
    d = CONTENT / partner
    items = [load_species(partner, f.stem) for f in d.glob("*.md")
             if f.stem != "partner"]
    # héroes primero, luego por nombre científico
    return sorted(items, key=lambda s: (not s.get("hero"), s.get("scientific_name", "")))
```
> Nota: `lru_cache` = contenido en memoria; se refresca al reiniciar el proceso
> (que es lo que pasa en cada deploy). Suficiente para contenido que cambia poco.

### `aliados/routes.py`
```python
from datetime import date
from flask import render_template, abort, Response, url_for
from . import aliados
from .content import load_partner, load_species, list_species, list_partners

@aliados.route("/")
def index():
    return render_template("aliados/index.html", partners=list_partners())

@aliados.route("/<partner>/")
def pillar(partner):
    p = load_partner(partner) or abort(404)
    return render_template("aliados/pillar.html",
                           partner=p, species=list_species(partner))

@aliados.route("/<partner>/<species>")
def species(partner, species):
    p = load_partner(partner) or abort(404)
    s = load_species(partner, species) or abort(404)
    return render_template("aliados/species.html", partner=p, species=s)

@aliados.route("/sitemap.xml")
def sitemap():
    urls = []
    for p in list_partners():
        urls.append(url_for("aliados.pillar", partner=p["slug"], _external=True))
        for s in list_species(p["slug"]):
            urls.append(url_for("aliados.species",
                                partner=p["slug"], species=s["slug"], _external=True))
    xml = render_template("aliados/sitemap.xml", urls=urls,
                          lastmod=date.today().isoformat())
    return Response(xml, mimetype="application/xml")
```

---

## 7. Plantillas (lo esencial)

### `_jsonld.html` (macro Product)
```jinja
{% macro product_jsonld(s, partner, request) %}
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "name": "{{ s.meta_title or s.scientific_name }}",
  "alternateName": {{ s.common_names | tojson }},
  "description": "{{ s.meta_description }}",
  "brand": {"@type": "Brand", "name": "{{ partner.partner_name }}"},
  "image": "{{ request.url_root.rstrip('/') ~ s.image }}",
  "offers": {
    "@type": "Offer",
    "availability": "https://schema.org/{{ s.availability }}",
    "priceCurrency": "COP",
    "url": "{{ request.url }}",
    "seller": {"@type": "LocalBusiness", "name": "{{ partner.partner_name }}", "areaServed": "CO"}
  }
}
</script>
{% endmacro %}
```

### `base.html` (cabecera SEO — layout propio)
```jinja
<!doctype html><html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}{% endblock %}</title>
<meta name="description" content="{% block description %}{% endblock %}">
<link rel="canonical" href="{{ request.url }}">
<meta property="og:type" content="website">
<meta property="og:title" content="{{ self.title() }}">
<meta property="og:description" content="{{ self.description() }}">
<meta property="og:url" content="{{ request.url }}">
{% block head_extra %}{% endblock %}
<link rel="stylesheet" href="{{ url_for('aliados.static', filename='aliados.css') }}">
</head><body>
{% block breadcrumbs %}{% endblock %}
{% block content %}{% endblock %}
</body></html>
```

`species.html` extiende `base.html`, imprime `s.body_html`, incluye el macro
JSON-LD y un breadcrumb (Inicio › Pilar › Especie). `pillar.html` recorre
`species` agrupando por `cluster` y muestra la banda de héroes (`hero == true`).

---

## 8. Checklist de SEO técnico

- [ ] `<title>` y meta description por página (desde frontmatter).
- [ ] `<link rel="canonical">` explícito y consistente con la convención de slash.
- [ ] JSON-LD: `Product` (spokes) + `CollectionPage`/`ItemList` (pilar) + `BreadcrumbList`.
- [ ] `sitemap.xml` dinámico (§6) — enviar en Google Search Console.
- [ ] `robots.txt` que permita rastreo y apunte al sitemap.
- [ ] Open Graph / Twitter cards para compartir.
- [ ] Breadcrumbs visibles + schema.
- [ ] Convención de trailing slash fija (pilar con `/`, spokes sin `/`); 301 lo demás.
- [ ] Imágenes con `alt`, tamaño razonable, `loading="lazy"`.
- [ ] `hreflang` si más adelante hay versión en inglés (es = principal).

---

## 9. Render: dinámico vs. congelado

- **Dinámico** (default): Flask renderiza en cada request. Simple; agrega caché
  HTTP (`Cache-Control`) porque el contenido casi no cambia.
- **Estático con Frozen-Flask** (recomendado para máx. rendimiento e independencia):
  genera HTML plano en `build/` que puede servir nginx o incrustarse en el sitio
  actual bajo `/aliados/`. Sin runtime, imbatible en velocidad y resiliencia.

```python
# freeze.py
from flask_frozen import Freezer
from your_app import app          # app con el blueprint registrado
freezer = Freezer(app)
if __name__ == "__main__":
    freezer.freeze()              # escribe build/aliados/...
```

---

## 10. Montaje / despliegue

- **App Flask existente:** `app.register_blueprint(aliados)` y listo.
- **App independiente + nginx:**
  ```nginx
  location /aliados/ {
      proxy_pass http://127.0.0.1:8010;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-Proto $scheme;
  }
  ```
- **Combinar dos apps WSGI** sin nginx: `werkzeug.middleware.dispatcher.DispatcherMiddleware`.
- **Estático (Frozen-Flask):** copiar `build/aliados/` al docroot del sitio actual.

`requirements.txt`: `Flask`, `python-frontmatter`, `Markdown`, y opcional `Frozen-Flask`.

---

## 11. Secuencia de construcción

1. Scaffold del blueprint + `content/` y registrar la ruta.
2. Convertir los 2 borradores actuales en `partner.md` + `chachafruto.md` /
   `guamo.md` / `comino-crespo.md` (agregar frontmatter).
3. Plantillas `base` / `pillar` / `species` + macro JSON-LD + CSS propio.
4. `sitemap.xml` + `robots.txt` + canonical/OG.
5. Completar las 14 especies (tras verificar nombres comunes ⚠).
6. Elegir render (dinámico o Frozen) y montar (§10).
7. Enviar sitemap a Search Console y validar con Rich Results Test.
