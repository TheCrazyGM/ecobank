import random
from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
    abort,
    send_from_directory,
    current_app,
)
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app.extensions import db, cache
from app.main import bp
from app.models import HiveAccount, User
from app.utils.hive import (
    fetch_post,
    fetch_user_blog,
    fetch_user_profile,
    fetch_account_wallet,
    fetch_posts_by_tag,
)


@bp.route("/robots.txt")
def robots_txt():
    if not current_app.static_folder:
        abort(404)
    return send_from_directory(current_app.static_folder, "robots.txt")


@bp.route("/")
@cache.cached(timeout=300, unless=lambda: current_user.is_authenticated)
def index():
    usernames_to_fetch = []

    if current_user.is_authenticated:
        # Get current user's hive accounts
        usernames_to_fetch = [acc.username for acc in current_user.hive_accounts]

        # If they have no accounts, maybe show some random community ones?
        if not usernames_to_fetch:
            all_accounts = (
                HiveAccount.query.order_by(HiveAccount.created_at.desc())
                .limit(20)
                .all()
            )
            usernames_to_fetch = [acc.username for acc in all_accounts]
        feed_title = _("My Feed")
    else:
        # Get public feed: latest created accounts (proxy for activity)
        all_accounts = (
            HiveAccount.query.order_by(HiveAccount.created_at.desc()).limit(20).all()
        )
        usernames_to_fetch = [acc.username for acc in all_accounts]
        feed_title = _("Community Feed")

    # Shuffle and limit to avoid hammering API
    random.shuffle(usernames_to_fetch)
    usernames_to_fetch = usernames_to_fetch[:5]  # Fetch max 5 users

    aggregated_posts = []

    for username in usernames_to_fetch:
        # Fetch top 4 posts per user (5 users * 4 posts = 20 total)
        entries, _next_cursor = fetch_user_blog(username, limit=4)
        aggregated_posts.extend(entries)

    # ------------------ FALLBACK LOGIC ------------------
    # If no posts found (e.g. empty feed or no accounts), fetch posts from "@restore.world"
    if not aggregated_posts:
        entries, _fallback_cursor = fetch_user_blog("restore.world", limit=20)
        aggregated_posts.extend(entries)
    # ----------------------------------------------------

    # Sort by created date desc (if we can parse it, otherwise simple string sort might be off but okay)
    # The utils return normalized string, so let's try to just show them.
    # Ideal would be parsing ISO format back to datetime for sort.
    aggregated_posts.sort(key=lambda x: x["created"], reverse=True)

    return render_template("index.html", posts=aggregated_posts, feed_title=feed_title)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.first_name = request.form.get("first_name", "").strip()
        current_user.last_name = request.form.get("last_name", "").strip()
        current_user.bio = request.form.get("bio", "").strip()
        current_user.avatar_url = request.form.get("avatar_url", "").strip()
        current_user.locale = request.form.get("locale", "en")

        try:
            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating profile: {e}", "danger")

        return redirect(url_for("main.profile"))

    return render_template("main/profile.html", user=current_user)


@bp.route("/u/<username>")
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    aggregated_posts = []

    # Get all linked Hive Accounts
    # user.hive_accounts is a dynamic relationship, so we can use .all()
    # But wait, looking at models.py: hive_accounts = db.relationship("HiveAccount", backref="creator", lazy="dynamic")
    # Yes, .all() works.
    linked_accounts = user.hive_accounts.all()

    for account in linked_accounts:
        # Fetch recent posts for each account
        # Utilizing fetch_user_blog as used in index()
        entries, _ = fetch_user_blog(account.username, limit=5)
        aggregated_posts.extend(entries)

    # Sort aggregated posts by 'created' date desc
    # Note: 'created' is a string in the current fetch_user_blog implementation usually
    # To be safe and consistent with index(), we use same sort key.
    # Ideally we'd parse dates, but string sort is "good enough" for ISO-like strings often returned by Hive APIs.
    aggregated_posts.sort(key=lambda x: x.get("created", ""), reverse=True)

    return render_template(
        "main/user_profile.html",
        user=user,
        posts=aggregated_posts,
        linked_accounts=linked_accounts,
    )


# -------------------- Hive Social Endpoints --------------------


@bp.route("/@<username>")
def hive_user_blog(username):
    """Hive user blog roll (Posts Only): /@<username>"""
    start_author = request.args.get("start_author")
    start_permlink = request.args.get("start_permlink")

    profile = fetch_user_profile(username)
    if not profile:
        abort(404)

    entries, next_cursor = fetch_user_blog(
        username,
        limit=20,
        start_author=start_author,
        start_permlink=start_permlink,
        mode="posts",
    )

    return render_template(
        "hive/user_blog.html",
        username=username,
        profile=profile,
        entries=entries,
        next_cursor=next_cursor,
        current_tab="posts",
    )


@bp.route("/@<username>/feed")
def hive_user_reblogs(username):
    """Hive user reblogs (Feed): /@<username>/feed"""
    start_author = request.args.get("start_author")
    start_permlink = request.args.get("start_permlink")

    profile = fetch_user_profile(username)
    if not profile:
        abort(404)

    entries, next_cursor = fetch_user_blog(
        username,
        limit=20,
        start_author=start_author,
        start_permlink=start_permlink,
        mode="reblogs",
    )

    return render_template(
        "hive/user_blog.html",
        username=username,
        profile=profile,
        entries=entries,
        next_cursor=next_cursor,
        current_tab="reblogs",
    )


@bp.route("/@<username>/<permlink>")
def hive_view_post(username, permlink):
    """Hive post view: /@<username>/<permlink>"""
    post = fetch_post(username, permlink)
    if post:
        return render_template(
            "hive/post.html",
            post=post,
            author=post["author"],
            permlink=post["permlink"],
            community=post.get("community"),
            tags=post.get("tags"),
            active_votes=post.get("active_votes"),
            reblogged_by=post.get("reblogged_by"),
            payout=post.get("payout"),
        )
    abort(404)


@bp.route("/<community>/@<username>/<permlink>")
def hive_view_post_community(community, username, permlink):
    """Hive post view with community prefix: /<community>/@<username>/<permlink>"""
    # Logic is identical to standard post view, community param is just for URL structure/SEO
    return hive_view_post(username, permlink)


@bp.route("/@<username>/wallet")
def hive_view_wallet(username):
    """Hive wallet view: /@<username>/wallet"""
    wallet = fetch_account_wallet(username)
    if not wallet:
        abort(404)
    return render_template("hive/wallet.html", wallet=wallet, username=username)


@bp.route("/tags/<tag>")
def hive_tag_feed(tag):
    """Hive posts by tag: /tags/<tag>"""
    start_author = request.args.get("start_author")
    start_permlink = request.args.get("start_permlink")

    entries, next_cursor = fetch_posts_by_tag(
        tag, limit=20, start_author=start_author, start_permlink=start_permlink
    )

    return render_template(
        "hive/tag_feed.html", tag=tag, entries=entries, next_cursor=next_cursor
    )


@bp.route("/about")
def about():
    return render_template("main/about.html", title=_("About Ecobank"))


@bp.route("/privacy")
def privacy():
    return render_template("main/privacy.html", title=_("Privacy Policy"))


@bp.route("/honey/trap")
def honey_trap():
    """Honeypot route. Logs IP and returns 403."""
    client_ip = request.remote_addr
    # Log specifically so UFW/Fail2Ban can pick it up
    current_app.logger.warning(
        f"HONEYPOT TRIGGERED: Client IP {client_ip} accessed the honeypot."
    )
    abort(403)
