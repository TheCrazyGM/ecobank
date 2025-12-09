import sqlalchemy as sa
from flask import abort, flash, redirect, render_template, request, url_for
from flask_babel import _
from flask_login import current_user, login_required

from app.extensions import db
from app.groups import bp
from app.models import Group, GroupMember, GroupResource, HiveAccount, User
from app.utils.notifications import create_notification


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        default_tags = request.form.get("default_tags")

        if not name:
            flash(_("Group name is required"), "danger")
            return redirect(url_for("groups.create"))

        existing = db.session.scalar(sa.select(Group).where(Group.name == name))
        if existing:
            flash(_("Group name already exists"), "danger")
            return redirect(url_for("groups.create"))

        group = Group(
            name=name,
            description=description,
            default_tags=default_tags,
            owner_user_id=current_user.id,
        )
        db.session.add(group)
        db.session.flush()  # Get ID

        # Add owner as member with 'owner' role
        member = GroupMember(group_id=group.id, user_id=current_user.id, role="owner")
        db.session.add(member)
        db.session.commit()

        flash(_('Group "%(name)s" created!', name=name), "success")
        return redirect(url_for("groups.view", id=group.id))

    return render_template("groups/create.html")


@bp.route("/<int:id>/edit", methods=["POST"])
@login_required
def edit_group(id):
    group = Group.query.get_or_404(id)

    # Check auth (owner/admin only)
    membership = GroupMember.query.filter_by(
        group_id=id, user_id=current_user.id
    ).first()
    if not membership or membership.role not in ["owner", "admin"]:
        flash(_("Unauthorized"), "danger")
        return redirect(url_for("groups.view", id=id))

    name = request.form.get("name")
    description = request.form.get("description")
    default_tags = request.form.get("default_tags")

    if not name:
        flash(_("Group name is required"), "danger")
        return redirect(url_for("groups.view", id=id))

    # Check name uniqueness if changed
    if name != group.name:
        existing = db.session.scalar(sa.select(Group).where(Group.name == name))
        if existing:
            flash(_("Group name already exists"), "danger")
            return redirect(url_for("groups.view", id=id))

    group.name = name
    group.description = description
    group.default_tags = default_tags
    db.session.commit()

    flash(_("Group settings updated."), "success")
    return redirect(url_for("groups.view", id=id))


@bp.route("/list")
@login_required
def list_groups():
    # Groups where user is a member
    memberships = GroupMember.query.filter_by(user_id=current_user.id).all()
    return render_template("groups/list.html", memberships=memberships)


@bp.route("/<int:id>")
@login_required
def view(id):
    group = Group.query.get_or_404(id)

    # Check membership
    membership = GroupMember.query.filter_by(
        group_id=id, user_id=current_user.id
    ).first()
    if not membership:
        flash("You are not a member of this group.", "danger")
        return redirect(url_for("groups.list_groups"))

    members = GroupMember.query.filter_by(group_id=id).join(User).all()
    resources = GroupResource.query.filter_by(group_id=id).all()

    # Get user's hive accounts to populate "Link Account" dropdown
    my_hive_accounts = HiveAccount.query.filter_by(created_by_id=current_user.id).all()

    # Filter out already linked accounts
    linked_usernames = [
        r.resource_id for r in resources if r.resource_type == "hive_account"
    ]
    available_accounts = [
        acc for acc in my_hive_accounts if acc.username not in linked_usernames
    ]

    # Fetch potential members (users not already in the group)
    # If user base grows large, this should be AJAX based, but fine for small scale
    existing_member_ids = [m.user_id for m in members]
    available_users_to_add = db.session.scalars(
        sa.select(User)
        .where(User.id.notin_(existing_member_ids))
        .order_by(User.username)
    ).all()

    return render_template(
        "groups/view.html",
        group=group,
        membership=membership,
        members=members,
        resources=resources,
        available_accounts=available_accounts,
        available_users_to_add=available_users_to_add,
    )


@bp.route("/<int:id>/add_member", methods=["POST"])
@login_required
def add_member(id):
    Group.query.get_or_404(id)

    # Check auth (owner or admin only)
    membership = GroupMember.query.filter_by(
        group_id=id, user_id=current_user.id
    ).first()
    if not membership or membership.role not in ["owner", "admin"]:
        flash("Unauthorized", "danger")
        return redirect(url_for("groups.view", id=id))

    username = request.form.get("username")
    user_to_add = db.session.scalar(sa.select(User).where(User.username == username))

    if not user_to_add:
        flash("User not found", "danger")
        return redirect(url_for("groups.view", id=id))

    # Check if already member
    existing = GroupMember.query.filter_by(group_id=id, user_id=user_to_add.id).first()
    if existing:
        flash("User is already a member", "info")
        return redirect(url_for("groups.view", id=id))

    new_member = GroupMember(group_id=id, user_id=user_to_add.id, role="member")
    db.session.add(new_member)
    db.session.commit()

    create_notification(
        user_id=user_to_add.id,
        message=f"You have been added to group '{Group.query.get(id).name}'",
        link=url_for("groups.view", id=id),
        type="invite",
    )

    flash(f"{username} added to group.", "success")
    return redirect(url_for("groups.view", id=id))


@bp.route("/<int:id>/remove_member/<int:user_id>", methods=["POST"])
@login_required
def remove_member(id, user_id):
    group = Group.query.get_or_404(id)

    # Check auth
    membership = GroupMember.query.filter_by(
        group_id=id, user_id=current_user.id
    ).first()
    if not membership or membership.role != "owner":
        flash("Unauthorized. Only owner can remove members.", "danger")
        return redirect(url_for("groups.view", id=id))

    if user_id == group.owner_user_id:
        flash("Cannot remove the owner.", "danger")
        return redirect(url_for("groups.view", id=id))

    member_to_remove = GroupMember.query.filter_by(group_id=id, user_id=user_id).first()
    if member_to_remove:
        db.session.delete(member_to_remove)
        db.session.commit()
        flash("Member removed.", "success")

    return redirect(url_for("groups.view", id=id))


@bp.route("/<int:id>/promote_member/<int:user_id>", methods=["POST"])
@login_required
def promote_member(id, user_id):
    Group.query.get_or_404(id)

    # Only owner can promote/demote for now
    membership = GroupMember.query.filter_by(
        group_id=id, user_id=current_user.id
    ).first()
    if not membership or membership.role != "owner":
        flash("Unauthorized", "danger")
        return redirect(url_for("groups.view", id=id))

    member = GroupMember.query.filter_by(group_id=id, user_id=user_id).first()
    if not member:
        flash("Member not found", "danger")
        return redirect(url_for("groups.view", id=id))

    # Simple cycle: member -> editor -> moderator -> member
    if member.role == "member":
        member.role = "editor"
    elif member.role == "editor":
        member.role = "moderator"

    db.session.commit()
    flash(f"Member promoted to {member.role}.", "success")
    return redirect(url_for("groups.view", id=id))


@bp.route("/<int:id>/demote_member/<int:user_id>", methods=["POST"])
@login_required
def demote_member(id, user_id):
    Group.query.get_or_404(id)

    membership = GroupMember.query.filter_by(
        group_id=id, user_id=current_user.id
    ).first()
    if not membership or membership.role != "owner":
        flash("Unauthorized", "danger")
        return redirect(url_for("groups.view", id=id))

    member = GroupMember.query.filter_by(group_id=id, user_id=user_id).first()
    if not member:
        flash("Member not found", "danger")
        return redirect(url_for("groups.view", id=id))

    # Simple cycle: moderator -> editor -> member
    if member.role == "moderator":
        member.role = "editor"
    elif member.role == "editor":
        member.role = "member"

    db.session.commit()
    flash(f"Member demoted to {member.role}.", "success")
    return redirect(url_for("groups.view", id=id))


@bp.route("/<int:id>/link_resource", methods=["POST"])
@login_required
def link_resource(id):
    Group.query.get_or_404(id)
    membership = GroupMember.query.filter_by(
        group_id=id, user_id=current_user.id
    ).first()

    if not membership:
        flash("Unauthorized", "danger")
        return redirect(url_for("groups.list_groups"))

    resource_type = request.form.get("resource_type")
    resource_id = request.form.get("resource_id")

    if resource_type == "hive_account":
        # Verify ownership of Hive Account
        account = HiveAccount.query.filter_by(
            username=resource_id, created_by_id=current_user.id
        ).first()
        if not account:
            flash("You do not own this Hive account.", "danger")
            return redirect(url_for("groups.view", id=id))

        # Create link
        link = GroupResource(
            group_id=id, resource_type="hive_account", resource_id=resource_id
        )
        db.session.add(link)
        db.session.commit()
        flash(f"Hive account {resource_id} linked to group.", "success")

    return redirect(url_for("groups.view", id=id))


@bp.route("/<int:id>/unlink_resource/<int:resource_id>", methods=["POST"])
@login_required
def unlink_resource(id, resource_id):
    Group.query.get_or_404(id)
    # Logic for who can unlink?
    # 1. The group owner/admin
    # 2. The owner of the resource (if we tracked who added it, currently we don't explicitly track who added the resource link, but we can infer from HiveAccount ownership)

    membership = GroupMember.query.filter_by(
        group_id=id, user_id=current_user.id
    ).first()
    if not membership:
        abort(403)

    resource = GroupResource.query.get_or_404(resource_id)

    can_delete = False
    if membership.role in ["owner", "admin"]:
        can_delete = True
    elif resource.resource_type == "hive_account":
        # Check if current user owns the hive account
        account = HiveAccount.query.filter_by(
            username=resource.resource_id, created_by_id=current_user.id
        ).first()
        if account:
            can_delete = True

    if can_delete:
        db.session.delete(resource)
        db.session.commit()
        flash("Resource unlinked.", "success")
    else:
        flash("Unauthorized to unlink this resource.", "danger")

    return redirect(url_for("groups.view", id=id))
