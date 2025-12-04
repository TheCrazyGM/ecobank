from flask import render_template, flash, redirect, url_for, request
from flask_babel import gettext as _
from app.admin import bp
from app.admin.decorators import admin_required
from app.admin.forms import AdminUserEditForm, AdminGroupEditForm
from app.models import User, Group, Draft, HiveAccount, PayPalOrder
from app.extensions import db


@bp.route("/")
@admin_required
def dashboard():
    user_count = User.query.count()
    group_count = Group.query.count()
    draft_count = Draft.query.count()
    hive_account_count = HiveAccount.query.count()
    return render_template(
        "admin/dashboard.html",
        user_count=user_count,
        group_count=group_count,
        draft_count=draft_count,
        hive_account_count=hive_account_count,
    )


@bp.route("/users")
@admin_required
def manage_users():
    users = User.query.order_by(User.id.desc()).limit(50).all()
    return render_template("admin/users.html", users=users)


@bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminUserEditForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        if form.account_credits.data is not None:
            user.account_credits = form.account_credits.data
        if form.password.data:
            user.set_password(form.password.data)
            flash(
                _("Password reset for user %(username)s.", username=user.username),
                "warning",
            )

        db.session.commit()
        flash(
            _("User %(username)s updated successfully.", username=user.username),
            "success",
        )
        return redirect(url_for("admin.manage_users"))
    return render_template("admin/user_edit.html", form=form, user=user)


@bp.route("/users/grant_credits/<int:user_id>", methods=["POST"])
@admin_required
def grant_credits(user_id):
    user = User.query.get_or_404(user_id)
    amount = int(request.form.get("amount", 0))
    user.account_credits += amount
    db.session.commit()
    flash(
        _("Credits updated for user %(username)s.", username=user.username), "success"
    )
    return redirect(url_for("admin.manage_users"))


@bp.route("/groups")
@admin_required
def manage_groups():
    groups = Group.query.order_by(Group.created_at.desc()).limit(50).all()
    return render_template("admin/groups.html", groups=groups)


@bp.route("/groups/edit/<int:group_id>", methods=["GET", "POST"])
@admin_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)
    form = AdminGroupEditForm(obj=group)
    # Pre-fill owner username manually since it's a relationship
    if request.method == "GET":
        form.owner_username.data = group.owner.username

    if form.validate_on_submit():
        group.name = form.name.data
        group.description = form.description.data

        # Handle owner change
        new_owner = User.query.filter_by(username=form.owner_username.data).first()
        if new_owner:
            group.owner = new_owner
        else:
            flash(
                _(
                    "User %(username)s not found. Owner not changed.",
                    username=form.owner_username.data,
                ),
                "danger",
            )
            return render_template("admin/group_edit.html", form=form, group=group)

        db.session.commit()
        flash(_("Group %(name)s updated successfully.", name=group.name), "success")
        return redirect(url_for("admin.manage_groups"))
    return render_template("admin/group_edit.html", form=form, group=group)


@bp.route("/posts")
@admin_required
def manage_posts():
    drafts = Draft.query.order_by(Draft.updated_at.desc()).limit(50).all()
    return render_template("admin/posts.html", drafts=drafts)


@bp.route("/logs/paypal")
@admin_required
def logs_paypal():
    orders = PayPalOrder.query.order_by(PayPalOrder.created_at.desc()).limit(50).all()
    return render_template("admin/logs_paypal.html", orders=orders)


@bp.route("/logs/hive")
@admin_required
def logs_hive():
    accounts = HiveAccount.query.order_by(HiveAccount.created_at.desc()).limit(50).all()
    return render_template("admin/logs_hive.html", accounts=accounts)
