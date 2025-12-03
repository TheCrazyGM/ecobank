import json
import random
import re
import string
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from nectar import Hive

from app.drafts import bp
from app.extensions import db
from app.models import (
    Draft,
    Group,
    GroupMember,
    GroupResource,
    HiveAccount,
)
from app.utils.markdown_render import render_markdown


# Helper for generating permlinks
def generate_permlink(title):
    # Simple permlink generation: lowercase, slugify
    s = title.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    if not s:
        s = "".join(random.choices(string.ascii_lowercase, k=10))
    return (
        s + "-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    )


@bp.route("/create/<int:group_id>", methods=["GET", "POST"])
@login_required
def create(group_id):
    group = Group.query.get_or_404(group_id)

    # Check membership
    membership = GroupMember.query.filter_by(
        group_id=group_id, user_id=current_user.id
    ).first()
    if not membership:
        flash("Unauthorized", "danger")
        return redirect(url_for("groups.list_groups"))

    # Get available shared accounts
    resources = GroupResource.query.filter_by(
        group_id=group_id, resource_type="hive_account"
    ).all()
    hive_accounts = [r.resource_id for r in resources]

    if request.method == "POST":
        title = request.form.get("title")
        body = request.form.get("body")
        tags = request.form.get("tags")
        hive_account = request.form.get("hive_account")

        if not title or not body or not hive_account:
            flash("Title, body and hive account are required", "danger")
            return redirect(url_for("drafts.create", group_id=group_id))

        if hive_account not in hive_accounts:
            flash("Invalid hive account selected", "danger")
            return redirect(url_for("drafts.create", group_id=group_id))

        draft = Draft(
            group_id=group_id,
            author_user_id=current_user.id,
            hive_account_username=hive_account,
            title=title,
            body=body,
            tags=tags,
            permlink=generate_permlink(title),
            status="draft",
        )
        db.session.add(draft)
        db.session.commit()

        flash("Draft created.", "success")
        return redirect(url_for("drafts.view", draft_id=draft.id))

    return render_template(
        "drafts/create.html", group=group, hive_accounts=hive_accounts
    )


@bp.route("/edit/<int:draft_id>", methods=["GET", "POST"])
@login_required
def edit(draft_id):
    draft = Draft.query.get_or_404(draft_id)
    group = Group.query.get(draft.group_id)

    # Check Permissions
    # Moderator or above (Owner, Admin, Editor - assuming 'admin' maps to Editor/Owner level rights or better)
    # Also allow the original author to edit their own draft if it's still a draft
    membership = GroupMember.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()
    if not membership:
        abort(403)

    can_edit = False
    if membership.role in ["owner", "admin", "moderator", "editor"]:
        can_edit = True
    elif draft.author_user_id == current_user.id:
        can_edit = True

    if not can_edit:
        flash("You do not have permission to edit this draft.", "danger")
        return redirect(url_for("groups.view", id=group.id))

    if draft.status == "published":
        flash("Cannot edit published posts.", "warning")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    # Get available shared accounts (in case they want to switch, though logic might be simpler to lock it)
    resources = GroupResource.query.filter_by(
        group_id=group.id, resource_type="hive_account"
    ).all()
    hive_accounts = [r.resource_id for r in resources]

    if request.method == "POST":
        draft.title = request.form.get("title")
        draft.body = request.form.get("body")
        draft.tags = request.form.get("tags")
        draft.hive_account_username = request.form.get("hive_account")

        db.session.commit()
        flash("Draft updated.", "success")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    return render_template(
        "drafts/edit.html", draft=draft, group=group, hive_accounts=hive_accounts
    )


@bp.route("/view/<int:draft_id>")
@login_required
def view(draft_id):
    draft = Draft.query.get_or_404(draft_id)
    group = Group.query.get(draft.group_id)

    # Check membership
    membership = GroupMember.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()
    if not membership:
        abort(403)

    rendered_body = render_markdown(draft.body)

    # Permissions to submit
    can_submit = False
    if membership.role in ["owner", "admin", "editor"]:
        can_submit = True

    return render_template(
        "drafts/view.html",
        draft=draft,
        rendered_body=rendered_body,
        can_submit=can_submit,
        author=draft.author,
    )


@bp.route("/submit/<int:draft_id>", methods=["POST"])
@login_required
def submit(draft_id):
    draft = Draft.query.get_or_404(draft_id)
    group = Group.query.get(draft.group_id)

    # Check Permissions (Owner or Editor only)
    membership = GroupMember.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()
    if not membership or membership.role not in ["owner", "admin", "editor"]:
        flash("Unauthorized to submit drafts.", "danger")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    if draft.status == "published":
        flash("Already published.", "warning")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    # 1. Construct Header
    author = draft.author
    avatar_url = author.avatar_url or "https://via.placeholder.com/100"

    # Default bio if not set
    bio_text = author.bio or f"Member of {group.name}"

    header_html = f"""<table>
<tr>
<td>
<center><img src="{avatar_url}" style="border-radius: 50%; width: 100px; height: 100px;"/></center>
</td>
<td>
<span><h4>About the Author</h4></span>
<div><span><strong>{author.display_name}</strong></span> - 
<span>{bio_text}</span></div>
</td>
</tr>
</table>
<hr/>
"""
    final_body = header_html + draft.body

    # 2. Get Hive Credentials for the Group's Shared Account
    # We need to find the HiveAccount object that corresponds to draft.hive_account_username
    # But the HiveAccount object is linked to the USER who created it, not the group directly (GroupResource links them).
    # We need to query HiveAccount where username matches AND it is linked to this group.

    resource = GroupResource.query.filter_by(
        group_id=group.id,
        resource_type="hive_account",
        resource_id=draft.hive_account_username,
    ).first()

    if not resource:
        flash(
            f"Hive account {draft.hive_account_username} is no longer linked to this group.",
            "danger",
        )
        return redirect(url_for("drafts.view", draft_id=draft_id))

    # Find the actual HiveAccount record to get keys
    # Since username is unique in HiveAccount table (enforced by model), we can find it.
    hive_account_record = HiveAccount.query.filter_by(
        username=draft.hive_account_username
    ).first()

    if not hive_account_record:
        flash("Hive account credentials not found in database.", "danger")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    # Decrypt Keys
    encryption_key = current_app.config.get("HIVE_ENCRYPTION_KEY")
    if not encryption_key:
        current_app.logger.error("HIVE_ENCRYPTION_KEY not set in config")
        flash("System configuration error: Encryption key missing.", "danger")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    fernet = Fernet(encryption_key)
    try:
        keys_json = fernet.decrypt(hive_account_record.keys_enc.encode()).decode()
        keys_dict = json.loads(keys_json)
        posting_key = keys_dict.get("posting", {}).get("private")
    except Exception as e:
        current_app.logger.error(f"Decryption failed: {e}")
        flash("Failed to decrypt account keys.", "danger")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    if not posting_key:
        flash("Posting key not found for this account.", "danger")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    # 3. Broadcast to Hive
    try:
        hive = Hive(keys=[posting_key], nobroadcast=False)

        # Parse tags
        tag_list = [t.strip() for t in (draft.tags or "").split(" ") if t.strip()]
        if not tag_list:
            tag_list = ["ecobank"]

        # Construct metadata
        json_metadata = {"app": "ecobank/0.1", "format": "markdown", "tags": tag_list}

        tx = hive.post(
            title=draft.title,
            body=final_body,
            author=draft.hive_account_username,
            permlink=draft.permlink,
            json_metadata=json_metadata,
            tags=tag_list,
        )

        # Update Draft Status
        draft.status = "published"
        draft.published_at = datetime.now(timezone.utc)
        draft.tx_id = tx.get("trx_id") if tx else "unknown"
        db.session.commit()

        flash("Post published successfully to Hive!", "success")
        return redirect(url_for("groups.view", id=group.id))

    except Exception as e:
        current_app.logger.exception("Hive posting failed")
        flash(f"Posting failed: {str(e)}", "danger")
        return redirect(url_for("drafts.view", draft_id=draft_id))
