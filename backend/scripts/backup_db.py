import os
import datetime
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def backup_database():
    """
    Creates a timestamped backup of the production database.
    Requires pg_dump to be installed on the system.
    """
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ Error: DATABASE_URL not found in .env")
        return False

    # Create backups directory if it doesn't exist with restrictive permissions (0700)
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    try:
        os.chmod(backup_dir, 0o700)
    except Exception:
        pass

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"fuze_backup_{timestamp}.sql")

    # Pre-create backup file with restrictive permissions (0600)
    old_umask = None
    try:
        old_umask = os.umask(0o077)
        with open(backup_file, 'w'):
            pass
        os.chmod(backup_file, 0o600)
    except Exception:
        pass
    finally:
        if old_umask is not None:
            try:
                os.umask(old_umask)
            except Exception:
                pass

    print(f"🔍 Starting backup to {backup_file}...")
    
    try:
        # Use pg_dump to create a backup
        process = subprocess.Popen(
            ['pg_dump', db_url, '-f', backup_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print(f"✅ Backup successful: {backup_file}")
            return True
        else:
            print(f"❌ Backup failed: {stderr.decode()}")
            return False
    except FileNotFoundError:
        print("❌ Error: pg_dump not found. Please install PostgreSQL client tools.")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    backup_database()
