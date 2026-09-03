import json
import re

from cryptography.fernet import Fernet
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required
from nectar import Hive
from nectar.account import Account
from nectargraphenebase.account import PasswordKey, PrivateKey

from app.account import bp
from app.extensions import db
from app.models import HiveAccount
from app.utils.hive import delegate_vesting, hp_to_vests, fetch_pending_claimed_accounts

USERNAME_REGEX = re.compile(r"^(?=.{3,16}$)[a-z][a-z0-9]{2,}(?:[.-][a-z0-9]{3,})*$")


def is_valid_hive_username(username):
    if not username:
        return False
    if len(username) < 3 or len(username) > 16:
        return False
    if username.endswith(("-", ".")):
        return False
    if "--" in username or ".." in username or "-." in username or ".-" in username:
        return False
    return bool(USERNAME_REGEX.match(username))


@bp.route("/buy-credits")
@login_required
def buy_credits():
    system_account = current_app.config.get("HIVE_CLAIMER_ACCOUNT")
    hive_claim_tickets = 0
    if system_account:
        try:
            hive_claim_tickets = fetch_pending_claimed_accounts(system_account)
        except Exception as e:
            current_app.logger.error(f"Failed to fetch pending claims: {e}")

    return render_template(
        "account/buy_credits.html",
        client_id=current_app.config["PAYPAL_CLIENT_ID"],
        price=current_app.config["CREDIT_PRICE_USD"],
        hive_claim_tickets=hive_claim_tickets,
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "GET":
        return render_template("account/create.html")

    # POST Logic
    if current_user.account_credits < 1:
        flash(_("You do not have enough credits to create a profile."), "danger")
        return redirect(url_for("account.buy_credits"))

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not is_valid_hive_username(username):
        flash(_("Invalid username format."), "danger")
        return redirect(url_for("account.create"))

    if not password:
        flash(_("Password is required."), "danger")
        return redirect(url_for("account.create"))

    # Check if username exists on chain
    hive = Hive()
    try:
        Account(username, blockchain_instance=hive)
        flash(_("That profile name is already taken on Hive."), "danger")
        return redirect(url_for("account.create"))
    except Exception:
        pass  # Username is available

    # Create account
    claimer = current_app.config.get("HIVE_CLAIMER_ACCOUNT")
    claimer_key = current_app.config.get("HIVE_CLAIMER_KEY")

    if not claimer or not claimer_key:
        flash(_("Account creator not configured."), "danger")
        return redirect(url_for("account.create"))

    try:
        hive_creator = Hive(keys=[claimer_key], nobroadcast=False)
        tx = hive_creator.create_claimed_account(
            username, creator=claimer, password=password, storekeys=False
        )
    except Exception as e:
        current_app.logger.exception("Hive account creation failed")
        flash(_("Account creation failed: %(error)s", error=str(e)), "danger")
        return redirect(url_for("account.create"))

    # Generate and Encrypt Keys
    prefix = hive.prefix
    keys = {}
    for role in ["owner", "active", "posting", "memo"]:
        pk = PasswordKey(username, password, role=role, prefix=prefix)
        priv = pk.get_private_key()
        keys[role] = {
            "public": str(priv.pubkey),
            "private": str(priv),
        }

    encryption_key = current_app.config.get("HIVE_ENCRYPTION_KEY")
    if not encryption_key:
        flash(
            _("Encryption key not configured. Cannot save credentials safely."),
            "danger",
        )
        return redirect(url_for("account.create"))

    fernet = Fernet(encryption_key)
    keys_json = json.dumps(keys)

    new_account = HiveAccount(
        username=username,
        password_enc=fernet.encrypt(password.encode()).decode(),
        keys_enc=fernet.encrypt(keys_json.encode()).decode(),
        created_by_id=current_user.id,
        tx_id=tx.get("trx_id") if tx else "unknown",
    )

    # Deduct credit
    current_user.account_credits -= 1

    db.session.add(new_account)
    db.session.commit()

    # Delegate RC if configured
    delegation_amount_hp = current_app.config.get("HIVE_DELEGATION_AMOUNT", 0.0)
    if delegation_amount_hp > 0:
        delegator_account = current_app.config.get("HIVE_CLAIMER_ACCOUNT")
        delegator_key = current_app.config.get("HIVE_CLAIMER_KEY")
        if delegator_account and delegator_key:
            vests_to_delegate = hp_to_vests(delegation_amount_hp)
            if vests_to_delegate > 0:
                if delegate_vesting(
                    delegator_account, delegator_key, username, vests_to_delegate
                ):
                    flash(
                        _(
                            "Successfully delegated %(hp)s HP to %(username)s for Resource Credits!",
                            hp=delegation_amount_hp,
                            username=username,
                        ),
                        "info",
                    )
                else:
                    flash(
                        _(
                            "Failed to delegate RC to %(username)s. Please contact support.",
                            username=username,
                        ),
                        "warning",
                    )
            else:
                current_app.logger.warning(
                    f"Calculated 0 VESTS for {delegation_amount_hp} HP, not delegating."
                )
        else:
            current_app.logger.warning(
                "HIVE_CLAIMER_ACCOUNT or HIVE_CLAIMER_KEY not set for delegation."
            )
            flash(
                _(
                    "RC delegation not configured. Account created but may have low Resource Credits."
                ),
                "warning",
            )
    else:
        flash(_("RC delegation amount is 0, skipping delegation."), "info")

    flash(
        _("Digital profile %(username)s created successfully!", username=username),
        "success",
    )
    return redirect(url_for("account.list_accounts"))


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_account():
    if request.method == "GET":
        return render_template("account/import.html")

    username = request.form.get("username", "").strip().lower()

    posting_key = request.form.get("posting_key", "").strip()
    active_key = request.form.get("active_key", "").strip()
    memo_key = request.form.get("memo_key", "").strip()

    if not is_valid_hive_username(username):
        flash(_("Invalid username format."), "danger")
        return redirect(url_for("account.import_account"))

    # Check for existing import
    existing = HiveAccount.query.filter_by(
        username=username, created_by_id=current_user.id
    ).first()
    if existing:
        flash(_("You have already connected this profile."), "warning")
        return redirect(url_for("account.list_accounts"))

    # Validate against blockchain
    hive = Hive()
    try:
        acc = Account(username, blockchain_instance=hive)
    except Exception:
        flash(_("That profile was not found on the Hive network."), "danger")
        return redirect(url_for("account.import_account"))

    prefix = hive.prefix
    keys_to_save = {}
    verified = False

    # EcoBank never accepts a master password. Users connect a profile by
    # providing the specific private key(s) they choose to delegate; each is
    # verified against the account's on-chain authorities before being stored.
    # The owner key is never accepted or stored.
    def verify_key(role, private_wif):
        if not private_wif:
            return None
        try:
            priv = PrivateKey(private_wif, prefix=prefix)
            pub = str(priv.pubkey)

            # memo is stored on-chain directly as a string, not in key_auths
            if role == "memo":
                if acc.get("memo_key") == pub:
                    return {"public": pub, "private": str(priv)}
            else:
                role_auths = acc.get(role, {}).get("key_auths", [])
                auth_keys = [k[0] for k in role_auths]
                if pub in auth_keys:
                    return {"public": pub, "private": str(priv)}
        except Exception:
            pass
        return None

    for role, wif in (
        ("posting", posting_key),
        ("active", active_key),
        ("memo", memo_key),
    ):
        res = verify_key(role, wif)
        if res:
            keys_to_save[role] = res
            verified = True

    if not verified:
        flash(
            _("No valid keys provided that match the profile's on-chain authorities."),
            "danger",
        )
        return redirect(url_for("account.import_account"))

    # Save to DB
    encryption_key = current_app.config.get("HIVE_ENCRYPTION_KEY")
    if not encryption_key:
        flash(_("Encryption key error."), "danger")
        return redirect(url_for("account.list_accounts"))

    fernet = Fernet(encryption_key)

    # Connected profiles: EcoBank stores only the individual keys the user
    # chose to delegate. There is no master password to store.
    keys_enc = fernet.encrypt(json.dumps(keys_to_save).encode()).decode()

    new_account = HiveAccount(
        username=username,
        password_enc=None,
        keys_enc=keys_enc,
        created_by_id=current_user.id,
        tx_id="import",
    )
    db.session.add(new_account)
    db.session.commit()

    flash(
        _("Profile %(username)s connected successfully!", username=username), "success"
    )
    return redirect(url_for("account.list_accounts"))


@bp.route("/list")
@login_required
def list_accounts():
    accounts = HiveAccount.query.filter_by(created_by_id=current_user.id).all()
    return render_template("account/list.html", accounts=accounts)


@bp.route("/view/<int:id>", methods=["GET", "POST"])
@login_required
def view_account(id):
    account = HiveAccount.query.get_or_404(id)
    if account.created_by_id != current_user.id:
        flash(_("Unauthorized"), "danger")
        return redirect(url_for("account.list_accounts"))

    # Security Check
    verified = False
    if request.method == "POST":
        password = request.form.get("password")
        if current_user.check_password(password):
            verified = True
        else:
            flash(_("Invalid password"), "danger")

    if not verified:
        return render_template("account/verify.html", account=account)

    # Decryption Logic
    encryption_key = current_app.config.get("HIVE_ENCRYPTION_KEY")
    if not encryption_key:
        flash(
            _("Encryption key not configured. Cannot decrypt credentials safely."),
            "danger",
        )
        return redirect(url_for("account.list_accounts"))
    fernet = Fernet(encryption_key)

    try:
        password = None
        if account.password_enc:
            password = fernet.decrypt(account.password_enc.encode()).decode()

        keys = json.loads(fernet.decrypt(account.keys_enc.encode()).decode())
    except Exception:
        flash(_("Failed to decrypt credentials."), "danger")
        return redirect(url_for("account.list_accounts"))

    return render_template(
        "account/view.html", account=account, password=password, keys=keys
    )


@bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_account(id):
    account = HiveAccount.query.get_or_404(id)
    if account.created_by_id != current_user.id:
        flash(_("Unauthorized"), "danger")
        return redirect(url_for("account.list_accounts"))

    try:
        db.session.delete(account)
        db.session.commit()
        flash(
            _(
                "Profile %(username)s has been removed from EcoBank. Keep your recovery keys safe!",
                username=account.username,
            ),
            "success",
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting HiveAccount {account.username}: {e}")
        flash(
            _("Failed to remove the profile from EcoBank. Please try again."), "danger"
        )

    return redirect(url_for("account.list_accounts"))
