import argparse
import json
import os
import sys
from datetime import datetime
from cryptography.fernet import Fernet

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import HiveAccount


def backup_accounts(filename):
    """Backs up HiveAccount data to a JSON file."""
    accounts = HiveAccount.query.all()
    data = []
    for acc in accounts:
        data.append(
            {
                "id": acc.id,
                "username": acc.username,
                "password_enc": acc.password_enc,
                "keys_enc": acc.keys_enc,
                "created_by_id": acc.created_by_id,
            }
        )

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    print(f"[+] Backup saved to {filename}")


def rotate_keys(old_key, new_key, dry_run=False, ignore_errors=False):
    """Rotates keys for all HiveAccount entries."""
    if not old_key:
        print("[-] Error: Old encryption key not found.")
        return

    fernet_old = Fernet(old_key)
    fernet_new = Fernet(new_key)

    accounts = HiveAccount.query.all()
    print(f"[*] Found {len(accounts)} accounts to process.")

    changed_count = 0
    errors = 0

    for acc in accounts:
        try:
            # Decrypt with old key
            password = None
            if acc.password_enc:
                password = fernet_old.decrypt(acc.password_enc.encode()).decode()

            keys_json = None
            if acc.keys_enc:
                keys_json = fernet_old.decrypt(acc.keys_enc.encode()).decode()

            # Encrypt with new key
            if password:
                acc.password_enc = fernet_new.encrypt(password.encode()).decode()

            if keys_json:
                acc.keys_enc = fernet_new.encrypt(keys_json.encode()).decode()

            # Verify immediately
            if password:
                decrypted_pass = fernet_new.decrypt(acc.password_enc.encode()).decode()
                if decrypted_pass != password:
                    raise Exception("Verification failed for password")

            if keys_json:
                decrypted_keys = fernet_new.decrypt(acc.keys_enc.encode()).decode()
                if decrypted_keys != keys_json:
                    raise Exception("Verification failed for keys")

            changed_count += 1
            if dry_run:
                print(f"[Dry Run] Rotated keys for user: {acc.username}")

        except Exception as e:
            print(f"[-] Error processing account {acc.username}: {repr(e)}")
            errors += 1
            if not dry_run:
                # In real run, we might want to stop or continue?
                # For safety, let's stop on error during rotation to avoid partial state if possible,
                # though individual row failures are handled by rollback if we commit at end?
                # Actually, we commit at the end.
                pass

    if dry_run:
        print(
            f"[*] Dry run complete. {changed_count} accounts would be updated. {errors} errors."
        )
        db.session.rollback()
    else:
        if errors > 0 and not ignore_errors:
            print(
                f"[-] Encountered {errors} errors. Rolling back changes. Use --ignore-errors to proceed anyway."
            )
            db.session.rollback()
        else:
            if errors > 0:
                print(
                    f"[!] Encountered {errors} errors but verifying commit due to --ignore-errors."
                )

            db.session.commit()
            print(f"[+] Successfully rotated keys for {changed_count} accounts.")
            print("\n[IMPORTANT] UPDATE YOUR .ENV FILE WITH THE NEW KEY:")
            print(f"HIVE_ENCRYPTION_KEY={new_key}\n")


def main():
    parser = argparse.ArgumentParser(description="Rotate Fernet keys for HiveAccount")
    parser.add_argument("--old-key", help="Current encryption key (defaults to .env)")
    parser.add_argument(
        "--new-key", help="New encryption key (optional, generated if not provided)"
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="Skip backup (NOT RECOMMENDED)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate without committing changes"
    )
    parser.add_argument(
        "--ignore-errors",
        action="store_true",
        help="Commit changes even if some records fail",
    )

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Get old key from args or config
        old_key = args.old_key or app.config.get("HIVE_ENCRYPTION_KEY")
        if not old_key:
            print("[-] No old key provided or found in config.")
            return

        # Generate new key if not provided
        new_key = args.new_key
        if not new_key:
            new_key = Fernet.generate_key().decode()
            print(f"[*] Generated new key: {new_key}")

        # Backup
        if not args.no_backup:
            backup_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(
                backup_dir, f"hive_accounts_backup_{timestamp}.json"
            )
            backup_accounts(backup_file)

        # Rotate
        rotate_keys(old_key.strip(), new_key.strip(), args.dry_run, args.ignore_errors)


if __name__ == "__main__":
    main()
