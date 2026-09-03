"""Permanent redirects for URLs that changed.

Kept deliberately small. Each entry is a path prefix that moved; requests to
the old prefix get a 301 to the new one, query string preserved.
"""

from flask import Flask, redirect, request

# old prefix -> new prefix (both without trailing slash)
_MOVED_PREFIXES = {
    "/groups": "/circles",
    "/admin/groups": "/admin/circles",
}


def init_app(app: Flask) -> Flask:
    for old, new in _MOVED_PREFIXES.items():
        _register_prefix_redirect(app, old, new)
    return app


def _register_prefix_redirect(app: Flask, old: str, new: str) -> None:
    endpoint = f"_moved{old.replace('/', '_')}"

    def _view(subpath: str = ""):
        target = f"{new}/{subpath}" if subpath else new
        if request.query_string:
            target = f"{target}?{request.query_string.decode()}"
        return redirect(target, code=301)

    app.add_url_rule(old, endpoint, _view, defaults={"subpath": ""})
    app.add_url_rule(f"{old}/", f"{endpoint}_slash", _view, defaults={"subpath": ""})
    app.add_url_rule(f"{old}/<path:subpath>", f"{endpoint}_sub", _view)
