"""Self-contained blueprint for partner ("aliados") SEO landing pages.

Mount into an existing Flask app with a single line:

    from aliados import aliados
    app.register_blueprint(aliados)

Pages are served under /aliados/<pillar-slug>/[<species-slug>] and are
driven entirely by Markdown + frontmatter files in aliados/content/.
No database required.
"""
from flask import Blueprint

aliados = Blueprint(
    "aliados",
    __name__,
    url_prefix="/aliados",
    template_folder="templates",
    static_folder="static",
    static_url_path="/aliados/static",
)

from . import routes  # noqa: E402,F401  (registers the routes on import)
