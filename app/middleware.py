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
        html = b"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Check</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f0f0; }
                .box { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
            </style>
            <script>
                document.cookie = "d_sensor=" + Date.now() + "; path=/; max-age=3600";
                setTimeout(function(){ window.location.reload(); }, 2000);
            </script>
        </head>
        <body>
            <div class="box">
                <h2>Checking your browser...</h2>
                <p>Please wait a moment.</p>
            </div>
        </body>
        </html>
        """

        status = "200 OK"
        response_headers = [
            ("Content-Type", "text/html"),
            ("Content-Length", str(len(html))),
        ]

        start_response(status, response_headers)
        return [html]
