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

    # Create backups directory if it doesn't exist
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"fuze_backup_{timestamp}.sql")

    print(f"🔍 Starting backup to {backup_file}...")
    
    try:
        # Use pg_dump to create a backup
        # Note: We use the URL directly
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
