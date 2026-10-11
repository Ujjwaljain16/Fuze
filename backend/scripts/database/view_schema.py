import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import create_app
from models import db

app = create_app()
from models import User, Project, Task, SavedContent, Feedback
from sqlalchemy import inspect

def view_database_schema():
    """Display database schema and sample data"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("🗄️  FUZE DATABASE SCHEMA")
        print("=" * 50)
        
        # Get all table names
        tables = inspector.get_table_names()
        print(f"📋 Total Tables: {len(tables)}")
        print(f"📋 Tables: {', '.join(tables)}\n")
        
        # Show schema for each table
        for table_name in tables:
            print(f"📊 TABLE: {table_name.upper()}")
            print("-" * 30)
            
            # Get columns
            columns = inspector.get_columns(table_name)
            for column in columns:
                nullable = "NULL" if column['nullable'] else "NOT NULL"
                print(f"  • {column['name']}: {column['type']} ({nullable})")
            
            # Get sample data count
            try:
                if table_name == 'users':
                    count = User.query.count()
                elif table_name == 'projects':
                    count = Project.query.count()
                elif table_name == 'tasks':
                    count = Task.query.count()
                elif table_name == 'saved_content':
                    count = SavedContent.query.count()
                elif table_name == 'feedback':
                    count = Feedback.query.count()
                else:
                    count = 0
                print(f"  📈 Records: {count}")
            except:
                print("  📈 Records: Unable to count")
            
            print()
        
        # Show sample data
        print("📊 SAMPLE DATA")
        print("=" * 50)
        
        # Users
        users = User.query.limit(3).all()
        if users:
            print(f"👥 USERS ({len(users)} shown):")
            for user in users:
                print(f"  • ID: {user.id}, Username: {user.username}, Created: {user.created_at}")
            print()
        
        # Projects
        projects = Project.query.limit(3).all()
        if projects:
            print(f"📁 PROJECTS ({len(projects)} shown):")
            for project in projects:
                print(f"  • ID: {project.id}, Title: {project.title}, User: {project.user_id}")
            print()
        
        # Bookmarks
        bookmarks = SavedContent.query.limit(3).all()
        if bookmarks:
            print(f"🔖 BOOKMARKS ({len(bookmarks)} shown):")
            for bookmark in bookmarks:
                print(f"  • ID: {bookmark.id}, Title: {bookmark.title}, URL: {bookmark.url[:50]}...")
            print()
        
        # Tasks
        tasks = Task.query.limit(3).all()
        if tasks:
            print(f" TASKS ({len(tasks)} shown):")
            for task in tasks:
                print(f"  • ID: {task.id}, Title: {task.title}, Project: {task.project_id}")
            print()
        
        # Feedback
        feedbacks = Feedback.query.limit(3).all()
        if feedbacks:
            print(f"💬 FEEDBACK ({len(feedbacks)} shown):")
            for feedback in feedbacks:
                print(f"  • ID: {feedback.id}, Type: {feedback.feedback_type}, User: {feedback.user_id}")
            print()

if __name__ == "__main__":
    view_database_schema() 