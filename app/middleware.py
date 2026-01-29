class BrowserCheckMiddleware:
    """
    Middleware that checks for a 'd_sensor' cookie.
    If missing, it returns a lightweight HTML page that sets the cookie via JS and reloads.
    This filters out dumb bots/scrapers that don't execute JS.
    """

    def __init__(self, app, whitelist_paths=None):
        self.app = app
        self.whitelist_paths = whitelist_paths or []
        self.whitelist_paths.extend(["/static", "/robots.txt", "/favicon.ico"])

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")

        # 1. Bypass whitelist
        for w in self.whitelist_paths:
            if path.startswith(w):
                return self.app(environ, start_response)

        # 2. Check for cookie
        # Cookie format: "d_sensor=timestamp"
        cookie_header = environ.get("HTTP_COOKIE", "")

        if "d_sensor=" in cookie_header:
            # OPTIONAL: Validate timestamp age here if needed
            return self.app(environ, start_response)

        # 3. Serve Challenge Page (Lightweight, <1KB)
        # 4 second delay before reload to slow them down further
        # HTML is minified to save bandwidth
        html = b"""<!DOCTYPE html><html lang="en"><head><title>Ecobank Security Check</title><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet"><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.css"><meta http-equiv="refresh" content="5"><style>body{display:flex;justify-content:center;align-items:center;height:100vh;background-color:#212529;color:white}.card{background-color:#343a40;border:1px solid #495057;color:#e9ecef}.bi-leaf{color:#198754;font-size:3rem}</style><script>document.cookie="d_sensor="+Date.now()+"; path=/; max-age=3600; SameSite=Lax";setTimeout(function(){window.location.reload();},2000);</script></head><body><div class="container"><div class="row justify-content-center"><div class="col-md-6 col-lg-4"><div class="card shadow-lg p-4 text-center"><div class="card-body"><div class="mb-3"><i class="bi bi-shield-lock bi-leaf"></i></div><h3 class="card-title fw-bold mb-3">Ecobank Security</h3><div class="d-flex justify-content-center align-items-center mb-3"><div class="spinner-border text-success me-2" role="status"><span class="visually-hidden">Loading...</span></div><span>Verifying browser...</span></div><p class="text-white-50 small">This check is automatic. You will be redirected shortly.</p></div></div></div></div></div></body></html>"""

        status = "200 OK"
        response_headers = [
            ("Content-Type", "text/html"),
            ("Content-Length", str(len(html))),
        ]

        start_response(status, response_headers)
        return [html]
