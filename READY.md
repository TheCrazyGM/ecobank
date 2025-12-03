# EcoBank

Project skeleton initialized successfully.

## Setup
1.  Navigate to `ecobank/`.
2.  Run `uv sync` to install dependencies.
3.  Run `uv run init_db.py` to initialize the database.
4.  **Important:** Update `.env`:
    *   `HIVE_CLAIMER_KEY`: Active Private Key for `HIVE_CLAIMER_ACCOUNT`.
    *   `PAYPAL_CLIENT_ID`: PayPal Client ID (Sandbox/Live).
    *   `PAYPAL_CLIENT_SECRET`: PayPal Client Secret.
5.  Run `uv run flask run` to start the server.

## Features
- **Framework:** Flask + Bootstrap 5
- **Auth:** Flask-Login with SQLAlchemy (User model)
- **DB:** SQLite (default), configured for Postgres switch
- **i18n:** Flask-Babel setup (en/es)
- **Rendering:** Safe Markdown/HTML rendering for Hive posts (see `app/utils/markdown_render.py`)
- **Hive Account Creation:**
    - **Credits System:** Users need credits to create accounts.
    - **Purchase:** Buy credits via PayPal (`/account/buy-credits`).
    - **Admin Grant:** Admin (user `admin`) can grant credits via `/admin/credits`.
    - **Creation:** Create new Hive accounts via `/account/create`.
    - **Storage:** Securely stores keys (encrypted with Fernet) in the database.
    - **Management:** Lists user-created accounts with option to view keys.
- **Groups:**
    - **Create:** Users can create groups (`/groups/create`).
    - **Membership:** Group owners can add/remove members.
    - **Shared Resources:** Members can share their Hive Accounts with the group (`/groups/view/<id>`).
- **Drafting & Posting:**
    - **Create Drafts:** Members can create drafts for the group using shared Hive accounts.
    - **Edit:** Moderators+ (and authors) can edit drafts.
    - **Submit:** Owners/Editors can publish drafts to the Hive blockchain.
    - **Automatic Header:** Automatically prepends an "About the Author" HTML block to published posts.

## Structure
- `app/`: Application code
    - `main/`: Main routes (index, admin)
    - `auth/`: Authentication routes
    - `account/`: Account creation and management routes
    - `groups/`: Group management routes
    - `drafts/`: Draft creation and posting routes
    - `paypal/`: PayPal integration routes
    - `utils/`: Utilities (markdown rendering)
    - `templates/`: HTML templates
- `instance/`: Database file
- `translations/`: i18n translation files

## Configuration
- `HIVE_CLAIMER_ACCOUNT`: Account used to claim new accounts (default: `ecoinstats`).
- `HIVE_CLAIMER_KEY`: Active private key for the claimer account.
- `HIVE_ENCRYPTION_KEY`: Fernet key for encrypting stored user keys.
- `PAYPAL_CLIENT_ID`/`SECRET`: For processing credit purchases.
- `CREDIT_PRICE_USD`: Price per credit (default: 3.00).
