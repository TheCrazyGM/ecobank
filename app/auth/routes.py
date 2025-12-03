from urllib.parse import urlsplit

import sqlalchemy as sa
from flask import flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_user, logout_user

from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.extensions import db
from app.models import User


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
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("main.index")
        return redirect(next_page)
    return render_template("auth/login.html", title=_("Sign In"), form=form)


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are now a registered user!'), 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title=_('Register'), form=form)