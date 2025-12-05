import sqlalchemy as sa
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse

from app.auth import bp
from app.auth.forms import (
    ChangePasswordForm,
    LoginForm,
    RegistrationForm,
    ResetPasswordRequestForm,
    ResetPasswordForm,
)
from app.extensions import db
from app.models import User
from app.utils.email import send_email


def send_verification_email(user):
    token = user.get_email_verification_token()
    send_email(
        _("[EcoBank] Verify Your Email"),
        sender=current_app.config["ADMINS"][0],
        recipients=[user.email],
        text_body=render_template("email/verify_email.txt", user=user, token=token),
        html_body=render_template("email/verify_email.html", user=user, token=token),
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data)
        )

        if user is None or not user.check_password(form.password.data):
            flash(_("Invalid username or password"), "danger")

            return redirect(url_for("auth.login"))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or urlparse(next_page).netloc != "":
            next_page = url_for("main.index")
        return redirect(next_page)
    return render_template("auth/login.html", title=_("Sign In"), form=form)


@bp.route("/verify_email/<token>")
def verify_email(token):
    if current_user.is_authenticated and current_user.is_verified:
        return redirect(url_for("main.index"))

    user = User.verify_email_verification_token(token)
    if not user:
        flash(_("Verification link is invalid or has expired."), "danger")
        return redirect(url_for("main.index"))

    if user.is_verified:
        flash(_("Account already verified."), "info")
    else:
        user.is_verified = True
        db.session.commit()
        flash(_("Your account has been verified!"), "success")

    return redirect(url_for("main.index"))


@bp.route("/logout")
def logout():
    logout_user()

    return redirect(url_for("main.index"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Send verification email
        send_verification_email(user)

        flash(
            _(
                "Congratulations, you are now a registered user! Please check your email to verify your account."
            ),
            "success",
        )
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", title=_("Register"), form=form)


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash(_("Invalid current password."), "danger")

            return redirect(url_for("auth.change_password"))

        current_user.set_password(form.new_password.data)

        db.session.commit()

        flash(_("Your password has been updated."), "success")

        return redirect(url_for("main.profile"))

    return render_template(
        "auth/change_password.html", title=_("Change Password"), form=form
    )


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(
        _("[EcoBank] Reset Your Password"),
        sender=current_app.config["ADMINS"][0],
        recipients=[user.email],
        text_body=render_template("email/reset_password.txt", user=user, token=token),
        html_body=render_template("email/reset_password.html", user=user, token=token),
    )


@bp.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
        flash(_("Check your email for the instructions to reset your password"), "info")
        return redirect(url_for("auth.login"))
    return render_template(
        "auth/reset_password_request.html", title=_("Reset Password"), form=form
    )


@bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("main.index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_("Your password has been reset."), "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)
