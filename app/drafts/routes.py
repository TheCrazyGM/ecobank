import json
import random
import re
import string
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from nectar import Hive
from nectar.comment import Comment  # Import Comment

from app.drafts import bp
from app.extensions import db
from app.models import (
    Draft,
    DraftVersion,
    Group,
    GroupMember,
    GroupResource,
    HiveAccount,
)
from app.utils.markdown_render import render_markdown
from app.utils.notifications import create_notification


def _save_draft_version(draft: Draft, user_id: int, action: str):
    """Saves a snapshot of the draft to MongoDB as a new version."""
    try:
        # Find the last version number for this draft
        last_version = (
            DraftVersion.objects(draft_id=draft.id).order_by("-version_number").first()
        )
        next_version_number = (last_version.version_number + 1) if last_version else 1

        new_version = DraftVersion(
            draft_id=draft.id,
            version_number=next_version_number,
            title=draft.title,
            body=draft.body,
            tags=draft.tags,
            saved_by_user_id=user_id,
            saved_at=datetime.now(timezone.utc),
        )
        new_version.save()
        current_app.logger.info(
            f"Draft {draft.id} version {next_version_number} saved by user {user_id} for action: {action}"
        )
    except Exception as e:
        current_app.logger.error(
            f"Failed to save draft version for draft {draft.id}: {e}"
        )


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


@bp.route("/create", defaults={"group_id": None}, methods=["GET", "POST"])
@bp.route("/create/<int:group_id>", methods=["GET", "POST"])
@login_required
def create(group_id):
    group = None
    user_groups = []
    hive_accounts = []

    if group_id:
        group = Group.query.get_or_404(group_id)
        # Check membership
        membership = GroupMember.query.filter_by(
            group_id=group_id, user_id=current_user.id
        ).first()
        if not membership:
            flash("Unauthorized", "danger")
            return redirect(url_for("groups.list_groups"))

        # Get available shared accounts for this group
        resources = GroupResource.query.filter_by(
            group_id=group_id, resource_type="hive_account"
        ).all()
        hive_accounts = [r.resource_id for r in resources]
    else:
        # No group specified, get all groups user is a member of
        memberships = GroupMember.query.filter_by(user_id=current_user.id).all()
        user_groups = [m.group for m in memberships]
        if not user_groups:
            flash("You must belong to a group to create a draft.", "warning")
            return redirect(url_for("groups.create_group"))

        # If only one group, auto-select it
        if len(user_groups) == 1:
            return redirect(url_for("drafts.create", group_id=user_groups[0].id))

    if request.method == "POST":
        # If group wasn't in URL, it must be in form
        if not group_id:
            try:
                group_id = int(request.form.get("group_id"))
                group = Group.query.get(group_id)
                # Re-verify membership for the posted group
                membership = GroupMember.query.filter_by(
                    group_id=group_id, user_id=current_user.id
                ).first()
                if not membership:
                    abort(403)
            except (ValueError, TypeError):
                flash("Invalid group selected", "danger")
                return redirect(url_for("drafts.create"))

        title = request.form.get("title")
        body = request.form.get("body")
        tags = request.form.get("tags")
        hive_account = request.form.get("hive_account")

        if not title or not body or not hive_account:
            flash("Title, body and hive account are required", "danger")
            if group:
                return redirect(url_for("drafts.create", group_id=group.id))
            return redirect(url_for("drafts.create"))

        # Verify hive account belongs to group (if group was passed or selected)
        # If selected from dropdown, we need to re-fetch resources to verify
        resources = GroupResource.query.filter_by(
            group_id=group_id, resource_type="hive_account"
        ).all()
        valid_accounts = [r.resource_id for r in resources]

        if hive_account not in valid_accounts:
            flash("Invalid hive account selected for this group", "danger")
            if group:
                return redirect(url_for("drafts.create", group_id=group.id))
            return redirect(url_for("drafts.create"))

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

        # Save initial version to MongoDB
        _save_draft_version(draft, current_user.id, "created")

        flash("Draft created.", "success")
        return redirect(url_for("drafts.view", draft_id=draft.id))

    return render_template(
        "drafts/create.html",
        group=group,
        user_groups=user_groups,
        hive_accounts=hive_accounts,
    )


@bp.route("/edit/<int:draft_id>", methods=["GET", "POST"])
@login_required
def edit(draft_id):
    draft = Draft.query.get_or_404(draft_id)
    group = Group.query.get(draft.group_id)

    # Check Permissions
    # Moderator or above (Owner, Admin, Moderator, Editor)
    # Also allow the original author to edit their own draft if it's still a draft
    membership = GroupMember.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()
    if not membership:
        abort(403)

    can_edit = False
    # Roles that can edit ANY draft
    if membership.role in ["owner", "admin", "moderator", "editor"]:
        can_edit = True
    # Authors can always edit their own
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
        # Save current state as a version before updating
        _save_draft_version(draft, current_user.id, "updated")

        draft.title = request.form.get("title")
        draft.body = request.form.get("body")
        draft.tags = request.form.get("tags")
        draft.hive_account_username = request.form.get("hive_account")
        # draft.beneficiaries = request.form.get("beneficiaries", "[]") # Removed

        db.session.commit()

        # Notify author if someone else edited
        if draft.author_user_id != current_user.id:
            create_notification(
                user_id=draft.author_user_id,
                message=f"Your draft '{draft.title}' was updated by {current_user.username}",
                link=url_for("drafts.view", draft_id=draft.id),
                type="edit",
            )

        flash("Draft updated.", "success")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    return render_template(
        "drafts/edit.html", draft=draft, group=group, hive_accounts=hive_accounts
    )


@bp.route("/versions/<int:draft_id>")
@login_required
def history(draft_id):
    draft = Draft.query.get_or_404(draft_id)
    group = Group.query.get(draft.group_id)

    # Check Permissions (Member of group)
    membership = GroupMember.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()
    if not membership:
        abort(403)

    versions = DraftVersion.objects(draft_id=draft_id).order_by("-version_number")

    return render_template("drafts/history.html", draft=draft, versions=versions)


@bp.route("/versions/<int:draft_id>/restore/<int:version_num>", methods=["POST"])
@login_required
def restore(draft_id, version_num):
    draft = Draft.query.get_or_404(draft_id)
    group = Group.query.get(draft.group_id)

    # Permission check (can edit)
    membership = GroupMember.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()
    can_edit = False
    if membership and (
        membership.role in ["owner", "admin", "moderator", "editor"]
        or draft.author_user_id == current_user.id
    ):
        can_edit = True

    if not can_edit:
        flash("Unauthorized to restore versions.", "danger")
        return redirect(url_for("drafts.history", draft_id=draft_id))

    version = DraftVersion.objects(
        draft_id=draft_id, version_number=version_num
    ).first()
    if not version:
        flash("Version not found", "danger")
        return redirect(url_for("drafts.history", draft_id=draft_id))

    # Save current state as a version before restoring
    _save_draft_version(draft, current_user.id, f"restored from v{version_num}")

    # Restore
    draft.title = version.title
    draft.body = version.body
    draft.tags = version.tags
    # draft.beneficiaries = version.beneficiaries # Beneficiaries are silently set, so we don't restore them explicitly from history
    db.session.commit()

    flash(f"Restored version {version_num}.", "success")
    return redirect(url_for("drafts.view", draft_id=draft_id))


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

    # Permissions to submit: Owner or Moderator only
    can_submit = False
    if membership.role in ["owner", "moderator", "admin"]:
        can_submit = True

    # Permissions to edit
    can_edit = False
    if (
        membership.role in ["owner", "admin", "moderator", "editor"]
        or draft.author_user_id == current_user.id
    ):
        can_edit = True

    # Permissions to delete/reject (Owner, Moderator, or Author)
    can_delete = False
    if (
        membership.role in ["owner", "admin", "moderator"]
        or draft.author_user_id == current_user.id
    ):
        can_delete = True

    return render_template(
        "drafts/view.html",
        draft=draft,
        rendered_body=rendered_body,
        can_submit=can_submit,
        can_edit=can_edit,
        can_delete=can_delete,
        author=draft.author,
    )


@bp.route("/reject/<int:draft_id>", methods=["POST"])
@login_required
def reject(draft_id):
    draft = Draft.query.get_or_404(draft_id)
    group = Group.query.get(draft.group_id)

    # Check Permissions
    membership = GroupMember.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()

    can_delete = False
    if membership and (
        membership.role in ["owner", "admin", "moderator"]
        or draft.author_user_id == current_user.id
    ):
        can_delete = True

    if not can_delete:
        flash("Unauthorized to delete this draft.", "danger")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    if draft.status == "published":
        flash("Cannot delete published posts.", "warning")
        return redirect(url_for("drafts.view", draft_id=draft_id))

    db.session.delete(draft)
    db.session.commit()
    flash("Draft rejected/deleted.", "success")
    return redirect(url_for("groups.view", id=group.id))


@bp.route("/submit/<int:draft_id>", methods=["POST"])
@login_required
def submit(draft_id):
    draft = Draft.query.get_or_404(draft_id)
    group = Group.query.get(draft.group_id)

    # Check Permissions (Owner, Admin, Moderator only)
    membership = GroupMember.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()
    if not membership or membership.role not in ["owner", "admin", "moderator"]:
        flash(
            "Unauthorized to submit drafts. Only Owners and Moderators can publish.",
            "danger",
        )
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
        json_metadata = {
            "app": "ecobank/0.1",
            "format": "markdown",
            "tags": tag_list,
            "ecobank": {
                "author_id": draft.author_user_id,
                "author_username": author.username,
                "group_id": group.id,
                "group_name": group.name,
            },
        }

        # Post content
        tx = hive.post(
            title=draft.title,
            body=final_body,
            author=draft.hive_account_username,
            permlink=draft.permlink,
            json_metadata=json_metadata,
            tags=tag_list,
        )

        # Apply Comment Options (Beneficiaries) if any
        beneficiaries_list = []
        platform_account = current_app.config.get(
            "HIVE_CLAIMER_ACCOUNT"
        )  # Use claimer account as platform beneficiary

        if platform_account:
            # Platform takes 5%
            beneficiaries_list.append(
                {"account": platform_account, "weight": 500}
            )  # 500 = 5%

        # We enforce our platform fee. The draft.beneficiaries column is no longer used for dynamic user input.

        if beneficiaries_list:
            c = Comment(
                f"@{draft.hive_account_username}/{draft.permlink}",
                blockchain_instance=hive,
            )
            c.set_comment_options(beneficiaries=beneficiaries_list)

        # Update Draft Status
        draft.status = "published"
        draft.published_at = datetime.now(timezone.utc)
        draft.tx_id = tx.get("trx_id") if tx else "unknown"
        db.session.commit()

        if draft.author_user_id != current_user.id:
            create_notification(
                user_id=draft.author_user_id,
                message=f"Your draft '{draft.title}' has been published to Hive!",
                link=f"https://hive.blog/@{draft.hive_account_username}/{draft.permlink}",
                type="publish",
            )

        flash("Post published successfully to Hive!", "success")
        return redirect(url_for("groups.view", id=group.id))

    except Exception as e:
        current_app.logger.exception("Hive posting failed")
        flash(f"Posting failed: {str(e)}", "danger")
        return redirect(url_for("drafts.view", draft_id=draft_id))
