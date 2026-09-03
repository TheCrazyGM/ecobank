"""Response-header policy for EcoBank.

Currently this only controls search-engine indexing. The default is
``noindex, nofollow`` for every response; a small allowlist of genuinely
public marketing pages is exempt. This keeps authenticated app pages
(accounts, drafts, wallet, admin, the API) out of search results even if
``robots.txt`` is later opened up for the public pages.

CSP / other hardening headers can be added here later.
"""

from flask import Flask, request

# Endpoints whose responses may be indexed by search engines. Everything
# else receives ``X-Robots-Tag: noindex, nofollow``. Endpoint names are
# ``<blueprint>.<view>`` (or ``static`` for the asset route).
PUBLIC_ENDPOINTS = frozenset(
    {
        "static",
        "main.index",
        "main.about",
        "main.privacy",
        "main.security",
        "main.terms",
        "main.token_price",
    }
)


def init_app(app: Flask) -> Flask:
    @app.after_request
    def set_robots_tag(response):
        if request.endpoint not in PUBLIC_ENDPOINTS:
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response

    return app
