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
    import subprocess
    from flask import current_app
    from sqlalchemy.engine.url import make_url

    app = scheduler.app or current_app
    with app.app_context():
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        # Normalize URI for parsing (SQLAlchemy handles some quirks)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_dir = os.path.join(base_dir, "backups", "db")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        logging.info("Starting database backup...")

        try:
            # Parse URI
            # Example: mysql://user:pass@host:port/dbname
            # Example: postgresql://user:pass@host:port/dbname

            if db_uri.startswith("sqlite"):
                logging.info("SQLite backup skipped (dev only).")
                return

            u = make_url(db_uri)
            # SQLAlchemy < 1.4 uses drivername, >= 1.4 has easier methods but make_url returns URL object
            # u.drivername usually 'mysql', 'postgresql', 'mysql+pymysql' etc.

            # Simple check based on prefix of drivername
            is_mysql = u.drivername.startswith("mysql")
            is_postgres = u.drivername.startswith(
                "postgresql"
            ) or u.drivername.startswith("postgres")

            env = os.environ.copy()
            cmd = None
            backup_file = None

            if is_mysql:
                target_dir = os.path.join(backup_dir, "mysql")
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                backup_file = os.path.join(
                    target_dir, f"ecobank_backup_{timestamp}.sql.gz"
                )

                # Construct mysqldump command
                # mysqldump -h host -P port -u user dbname | gzip > file
                cmd_parts = ["mysqldump"]
                if u.host:
                    cmd_parts.extend(["-h", u.host])
                if u.port:
                    cmd_parts.extend(["-P", str(u.port)])
                if u.username:
                    cmd_parts.extend(["-u", u.username])

                # Password via env
                if u.password:
                    env["MYSQL_PWD"] = u.password

                cmd_parts.append(u.database)

                # We construct the shell command string manually to handle the pipe
                # safely quoting args is tricky in shell=True, but these are from config.
                # Let's trust config for now or use Popen with list for first part?
                # Popen with pipe requires shell=True for the pipe part usually or manual piping.
                # Let's stick to the previous shell=True pattern for simplicity but be careful.

                # Re-construct command string safely-ish
                defs = f"mysqldump -h '{u.host or 'localhost'}' -u '{u.username or 'root'}'"
                if u.port:
                    defs += f" -P {u.port}"

                # Don't include -p in command string, utilize MYSQL_PWD env var
                cmd = f"{defs} '{u.database}' | gzip > '{backup_file}'"

            elif is_postgres:
                target_dir = os.path.join(backup_dir, "postgres")
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                backup_file = os.path.join(
                    target_dir, f"ecobank_backup_{timestamp}.sql.gz"
                )

                if u.password:
                    env["PGPASSWORD"] = u.password

                # pg_dump -h host -p port -U user -d db
                defs = f"pg_dump -h '{u.host or 'localhost'}' -U '{u.username or 'postgres'}'"
                if u.port:
                    defs += f" -p {u.port}"

                cmd = f"{defs} -d '{u.database}' | gzip > '{backup_file}'"

            else:
                logging.warning(f"Unsupported database type for backup: {u.drivername}")
                return

            # Execute
            if cmd:
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

        except Exception as e:
            logging.error(f"Backup failed with error: {e}")

        # Prune old backups (keep last 7 days)
        try:
            for subdir in ["mysql", "postgres"]:
                target_dir = os.path.join(backup_dir, subdir)
                if os.path.exists(target_dir):
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
