"""Minimal example of mounting the aliados blueprint.

In your real app you already have `app = Flask(__name__)`; you only need
the two marked lines. Run this file directly to preview locally:

    pip install -r aliados/requirements.txt
    python example_app.py
    # visit http://127.0.0.1:8010/aliados/vivero-especies-nativas-colombia/
"""
from flask import Flask

app = Flask(__name__)

# --- the only two lines you add to an existing app -------------------
from aliados import aliados          # noqa: E402
app.register_blueprint(aliados)      # noqa: E402
# ---------------------------------------------------------------------

if __name__ == "__main__":
    app.run(port=8010, debug=True)
