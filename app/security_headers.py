"""Response-header policy for EcoBank.

This controls search-engine indexing and third-party browser resources. The default is
``noindex, nofollow`` for every response; a small allowlist of genuinely
public marketing pages is exempt. This keeps authenticated app pages
(accounts, drafts, wallet, admin, the API) out of search results even if
``robots.txt`` is later opened up for the public pages.

The PayPal SDK URL is parameterized per deployment, so it cannot use a stable
SRI hash; its origin is restricted by CSP instead. Fixed-version CDN resources
carry SRI attributes in the templates.
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
    content_security_policy = "; ".join(
        (
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'self'",
            "form-action 'self' https://*.paypal.com https://*.paypalobjects.com https://*.venmo.com",
            "img-src 'self' data: https:",
            "font-src 'self' https://cdn.jsdelivr.net https://*.paypal.com https://*.paypalobjects.com https://*.venmo.com",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://*.paypal.com https://*.paypalobjects.com https://*.venmo.com",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://*.paypal.com https://*.paypalobjects.com https://*.venmo.com",
            "connect-src 'self' https://*.paypal.com https://*.paypalobjects.com https://*.venmo.com",
            "child-src 'self' https://*.paypal.com https://*.paypalobjects.com https://*.venmo.com",
            "frame-src 'self' https://*.paypal.com https://*.paypalobjects.com https://*.venmo.com",
        )
    )

    @app.after_request
    def set_security_headers(response):
        if request.endpoint not in PUBLIC_ENDPOINTS:
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        response.headers.setdefault("Content-Security-Policy", content_security_policy)
        response.headers.setdefault(
            "Cross-Origin-Opener-Policy", "same-origin-allow-popups"
        )
        return response

    return app
