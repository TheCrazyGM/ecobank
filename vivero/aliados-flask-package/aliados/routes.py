"""Routes for the aliados blueprint."""
from datetime import date
from flask import render_template, abort, Response, request, url_for
from . import aliados
from . import content as C


@aliados.route("/")
def index():
    return render_template("aliados/index.html", partners=C.list_partners())


@aliados.route("/<partner>/")
def pillar(partner):
    p = C.load_partner(partner)
    if not p:
        abort(404)
    species = C.list_species(partner)
    schema = C.collection_graph(p, species, request.base_url, request.url_root)
    return render_template("aliados/pillar.html", partner=p, species=species, schema=schema)


@aliados.route("/<partner>/<species>")
def species(partner, species):
    p = C.load_partner(partner)
    s = C.load_species(partner, species)
    if not p or not s:
        abort(404)
    schema = C.product_graph(s, p, request.base_url, request.url_root)
    return render_template("aliados/species.html", partner=p, species=s, schema=schema)


@aliados.route("/sitemap.xml")
def sitemap():
    urls = []
    for p in C.list_partners():
        urls.append(url_for("aliados.pillar", partner=p["slug"], _external=True))
        for s in C.list_species(p["slug"]):
            urls.append(url_for("aliados.species", partner=p["slug"], species=s["slug"], _external=True))
    xml = render_template("aliados/sitemap.xml", urls=urls, lastmod=date.today().isoformat())
    return Response(xml, mimetype="application/xml")
