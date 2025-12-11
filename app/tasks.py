from app.extensions import db, scheduler
from app.models import PayPalOrder
from datetime import datetime, timedelta, timezone
import logging


def run_paypal_maintenance():
    """
    Scheduled task to:
    1. Mark CREATED orders as EXPIRED if older than 24 hours.
    2. Hard delete EXPIRED/FAILED/DENIED orders older than 30 days.
    """
    # Use app context because we access DB
    from flask import current_app

    app = scheduler.app or current_app
    with app.app_context():
        now = datetime.now(timezone.utc)
        expiration_time = now - timedelta(hours=24)
        deletion_time = now - timedelta(days=30)

        # 1. Expire old pending orders
        old_orders = PayPalOrder.query.filter(
            PayPalOrder.status == "CREATED", PayPalOrder.created_at < expiration_time
        ).all()

        expired_count = 0
        for order in old_orders:
            order.status = "EXPIRED"
            expired_count += 1

        # 2. Hard delete old failed/expired orders
        orders_to_delete = PayPalOrder.query.filter(
            PayPalOrder.status.in_(["EXPIRED", "FAILED", "DENIED"]),
            PayPalOrder.created_at < deletion_time,
        ).all()

        deleted_count = 0
        for order in orders_to_delete:
            db.session.delete(order)
            deleted_count += 1

        if expired_count > 0 or deleted_count > 0:
            db.session.commit()
            logging.info(
                f"PayPal Maintenance: Expired {expired_count} orders, Deleted {deleted_count} old orders."
            )
        else:
            logging.info("PayPal Maintenance: No actions needed.")


def cleanup_draft_versions():
    """
    Scheduled task to remove version history for published drafts.
    """
    from flask import current_app
    from app.models import Draft, DraftVersion

    app = scheduler.app or current_app
    with app.app_context():
        # Find all published drafts
        published_drafts = Draft.query.filter_by(status="published").all()

        cleanup_count = 0
        version_count = 0

        for draft in published_drafts:
            # Delete versions for this draft
            deleted = DraftVersion.objects(draft_id=draft.id).delete()
            if deleted > 0:
                cleanup_count += 1
                version_count += deleted

        if version_count > 0:
            logging.info(
                f"Draft Cleanup: Removed {version_count} versions from {cleanup_count} published drafts."
            )
        else:
            logging.info("Draft Cleanup: No versions to clean up.")


def backup_database():
    """
    Scheduled task to backup the database.
    Supports SQLite (file copy) and Postgres (pg_dump).
    """
    import os
    import shutil
    import subprocess
    from flask import current_app

    app = scheduler.app or current_app
    with app.app_context():
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_dir = os.path.join(base_dir, "backups", "db")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        logging.info("Starting database backup...")

        try:
            if db_uri.startswith("sqlite"):
                # SQLite Backup
                target_dir = os.path.join(backup_dir, "sqlite")
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                # Extract file path from URI (sqlite:///path/to/db)
                db_path = db_uri.replace("sqlite:///", "")
                if not os.path.isabs(db_path):
                    db_path = os.path.join(base_dir, db_path)

                if os.path.exists(db_path):
                    backup_file = os.path.join(
                        target_dir, f"ecobank_backup_{timestamp}.db"
                    )
                    shutil.copy2(db_path, backup_file)
                    logging.info(f"Database backup successful: {backup_file}")
                else:
                    # Fallback: Check instance folder
                    instance_path = os.path.join(
                        base_dir, "instance", os.path.basename(db_path)
                    )
                    if os.path.exists(instance_path):
                        backup_file = os.path.join(
                            target_dir, f"ecobank_backup_{timestamp}.db"
                        )
                        shutil.copy2(instance_path, backup_file)
                        logging.info(
                            f"Database backup successful (from instance): {backup_file}"
                        )
                    else:
                        logging.error(
                            f"Database file not found at: {db_path} or {instance_path}"
                        )

            elif db_uri.startswith("postgresql"):
                # Postgres Backup
                target_dir = os.path.join(backup_dir, "postgres")
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                backup_file = os.path.join(
                    target_dir, f"ecobank_backup_{timestamp}.sql.gz"
                )

                # Use pg_dump
                # Assumes pg_dump is in PATH and .pgpass or trust auth is configured for non-interactive
                cmd = f"pg_dump '{db_uri}' | gzip > '{backup_file}'"

                # Security note: Passing password via URI in command line might be visible to ps.
                # Ideally use PGPASSWORD env var if needed.
                env = os.environ.copy()

                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate()

                if process.returncode == 0:
                    logging.info(f"Database backup successful: {backup_file}")
                else:
                    logging.error(f"Database backup failed: {stderr.decode()}")

            else:
                logging.warning(f"Unlock database type for backup: {db_uri}")

        except Exception as e:
            logging.error(f"Backup failed with error: {e}")

        # Prune old backups (keep last 7 days)
        try:
            target_dir = None
            if db_uri.startswith("sqlite"):
                target_dir = os.path.join(backup_dir, "sqlite")
            elif db_uri.startswith("postgresql"):
                target_dir = os.path.join(backup_dir, "postgres")

            if target_dir and os.path.exists(target_dir):
                purge_old_backups(target_dir, days=7)
        except Exception as e:
            logging.error(f"Pruning old backups failed: {e}")


def purge_old_backups(directory, days=7):
    """
    Deletes files in the directory older than the specified number of days.
    """
    import os
    import time

    if not os.path.exists(directory):
        return

    cutoff_time = time.time() - (days * 86400)

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff_time:
                try:
                    os.remove(file_path)
                    logging.info(f"Pruned old backup: {filename}")
                except Exception as e:
                    logging.error(f"Failed to prune {filename}: {e}")
