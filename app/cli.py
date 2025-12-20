import click
from datetime import datetime, timezone, timedelta
from flask.cli import with_appcontext
from sqlalchemy import or_

from app.extensions import db
from app.models import User


@click.command("cleanup-spam")
@click.option(
    "--force-legacy",
    is_flag=True,
    help="Force delete unverified users with no created_at timestamp.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting.",
)
@with_appcontext
def cleanup_spam(force_legacy, dry_run):
    """Deletes unverified users older than 7 days."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    # Base query: Unverified users
    query = User.query.filter_by(is_verified=False)

    # Filter: created_at < 7 days ago OR (created_at is NULL AND force_legacy is True)
    if force_legacy:
        # Delete if too old OR if None
        users_to_delete = query.filter(
            or_(User.created_at < cutoff, User.created_at.is_(None))
        ).all()
    else:
        # Only delete if specifically older than 7 days (ignores None)
        users_to_delete = query.filter(User.created_at < cutoff).all()

    count = len(users_to_delete)
    if count == 0:
        click.echo("No spam accounts found to cleanup.")
        return

    click.echo(f"Found {count} unverified spam accounts.")

    if dry_run:
        click.echo("DRY RUN: The following accounts would be deleted:")
        for user in users_to_delete:
            click.echo(
                f" - ID: {user.id}, Username: {user.username}, Email: {user.email}, Created: {user.created_at}"
            )
        click.echo("No changes made.")
        return

    if click.confirm(f"Are you sure you want to delete {count} accounts?"):
        for user in users_to_delete:
            db.session.delete(user)
        db.session.commit()
        click.echo("Cleanup complete.")
    else:
        click.echo("Aborted.")
