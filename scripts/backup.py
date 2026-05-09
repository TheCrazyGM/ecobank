import os
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

def run_backup():
    # Load environment variables from .env
    load_dotenv()
    
    db_uri = os.getenv("SQLALCHEMY_DATABASE_URI")
    if not db_uri:
        print("Error: SQLALCHEMY_DATABASE_URI not found in .env")
        return

    # Parse the URI
    # Example: mysql+pymysql://user:password@localhost/dbname
    parsed = urlparse(db_uri)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if "sqlite" in parsed.scheme:
        # SQLite backup is just a file copy
        db_path = db_uri.replace("sqlite:///", "")
        backup_file = f"backup_ecobank_{timestamp}.db"
        subprocess.run(["cp", db_path, backup_file])
        print(f"SQLite backup created: {backup_file}")

    elif "mysql" in parsed.scheme or "mariadb" in parsed.scheme:
        # MariaDB/MySQL backup
        db_name = parsed.path.lstrip('/')
        backup_file = f"backup_ecobank_{db_name}_{timestamp}.sql.gz"
        
        # Build the command
        # Note: We assume ~/.my.cnf is configured for auth or credentials are in the URI
        cmd = [
            "mariadb-dump",
            f"--user={parsed.username}",
            f"--password={parsed.password}",
            f"--host={parsed.hostname}",
            db_name
        ]
        
        with open(backup_file.replace(".gz", ""), "w") as f:
            subprocess.run(cmd, stdout=f, check=True)
            
        # Compress it
        subprocess.run(["gzip", backup_file.replace(".gz", "")])
        print(f"MariaDB backup created and compressed: {backup_file}")

if __name__ == "__main__":
    run_backup()
