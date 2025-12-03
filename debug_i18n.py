from app import create_app

app = create_app()
with app.app_context():
    print(f"App Root: {app.root_path}")
    print(f"Config TRANS_DIRS: {app.config['BABEL_TRANSLATION_DIRECTORIES']}")

    # Try to translate something
    from flask_babel import gettext as _

    print(f"Test 'Home': {_('Home')}")
    print(f"Test 'Create Draft': {_('Create Draft')}")

    # Check where it thinks translations are
    # Accessing private attribute just for debugging if possible, or checking behavior
