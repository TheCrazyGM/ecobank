import sqlalchemy as sa
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.main import bp
from app.models import User
from app.utils.markdown_render import render_markdown


@bp.route("/")
def index():
    sample_markdown = """
# Welcome to EcoBank

This is a sample Hive post rendered with **safe markdown**.

- Item 1
- Item 2

```python
def hello():
    print("Hello World")
```

![Image](https://via.placeholder.com/150)
    """
    rendered_content = render_markdown(sample_markdown)
    return render_template("index.html", content=rendered_content)


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


@bp.route("/admin/credits", methods=["GET", "POST"])
@login_required
def admin_credits():
    if current_user.username != "admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username")
        credits = int(request.form.get("credits", 0))

        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user:
            user.account_credits += credits
            db.session.commit()
            flash(
                f"Added {credits} credits to {username}. Total: {user.account_credits}",
                "success",
            )
        else:
            flash(f"User {username} not found.", "danger")

    return render_template("admin/credits.html")
