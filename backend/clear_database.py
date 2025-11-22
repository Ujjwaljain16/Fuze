#!/usr/bin/env python3
"""
🗑️ Complete Database Clearing Script for Fuze
Clears ALL user data while preserving database schema

WARNING: This will delete ALL data from the database!
Only use this for testing/development purposes.

Usage:
    python clear_database.py          # Interactive confirmation
    python clear_database.py --force  # Skip confirmation (dangerous!)
    python clear_database.py --dry-run # Show what would be deleted without actually deleting
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def clear_all_data(dry_run=False):
    """Clear all data from database while preserving schema"""
    try:
        from run_production import app, db
        from models import User, Project, Task, SavedContent, ContentAnalysis, Feedback, UserFeedback

        with app.app_context():
            print("🔍 Analyzing current database state..." if not dry_run else "🔍 DRY RUN: Analyzing current database state...")

            # Count records in each table
            counts = {
                'users': User.query.count(),
                'projects': Project.query.count(),
                'tasks': Task.query.count(),
                'saved_content': SavedContent.query.count(),
                'content_analysis': ContentAnalysis.query.count(),
                'feedback': Feedback.query.count(),
                'user_feedback': UserFeedback.query.count()
            }

            total_records = sum(counts.values())

            print(f"\n📊 Current Database Records:")
            print(f"   👥 Users: {counts['users']}")
            print(f"   📁 Projects: {counts['projects']}")
            print(f"    Tasks: {counts['tasks']}")
            print(f"   🔖 Saved Content: {counts['saved_content']}")
            print(f"   📈 Content Analysis: {counts['content_analysis']}")
            print(f"   💬 Feedback: {counts['feedback']}")
            print(f"   📊 User Feedback: {counts['user_feedback']}")
            print(f"   📈 TOTAL: {total_records} records")

            if total_records == 0:
                print("\n Database is already empty!")
                return True

            if dry_run:
                print("\n🔍 DRY RUN COMPLETE - No data was actually deleted")
                return True

            print(f"\n  WARNING: This will delete {total_records} records from ALL tables!")

            # Clear tables in correct order (respecting foreign keys)
            print("\n🗑️ Clearing tables...")

            # Clear tables with foreign key dependencies first
            deleted_counts = {}

            # Clear UserFeedback (no dependencies)
            deleted_counts['user_feedback'] = UserFeedback.query.delete()
            print(f"    Cleared {deleted_counts['user_feedback']} user feedback records")

            # Clear Feedback (depends on users, projects, saved_content)
            deleted_counts['feedback'] = Feedback.query.delete()
            print(f"    Cleared {deleted_counts['feedback']} feedback records")

            # Clear ContentAnalysis (depends on saved_content)
            deleted_counts['content_analysis'] = ContentAnalysis.query.delete()
            print(f"    Cleared {deleted_counts['content_analysis']} content analysis records")

            # Clear Tasks and Subtasks (depends on projects)
            # Note: Subtasks are cascade deleted when tasks are deleted
            deleted_counts['tasks'] = Task.query.delete()
            print(f"    Cleared {deleted_counts['tasks']} task records (including subtasks)")

            # Clear SavedContent (depends on users)
            deleted_counts['saved_content'] = SavedContent.query.delete()
            print(f"    Cleared {deleted_counts['saved_content']} saved content records")

            # Clear Projects (depends on users)
            deleted_counts['projects'] = Project.query.delete()
            print(f"    Cleared {deleted_counts['projects']} project records")

            # Clear Users last (other tables depend on it)
            deleted_counts['users'] = User.query.delete()
            print(f"    Cleared {deleted_counts['users']} user records")

            # Commit all changes
            db.session.commit()

            total_deleted = sum(deleted_counts.values())
            print(f"\n SUCCESS: Deleted {total_deleted} records total")

            # Verify everything is cleared
            verification_counts = {
                'users': User.query.count(),
                'projects': Project.query.count(),
                'tasks': Task.query.count(),
                'saved_content': SavedContent.query.count(),
                'content_analysis': ContentAnalysis.query.count(),
                'feedback': Feedback.query.count(),
                'user_feedback': UserFeedback.query.count()
            }

            remaining = sum(verification_counts.values())

            if remaining == 0:
                print(" VERIFICATION: All data successfully cleared!")
                print("\n🎉 Database is now ready for fresh user testing!")
                print("   - All user accounts removed")
                print("   - All projects, tasks, and content cleared")
                print("   - All feedback and analysis data removed")
                print("   - Schema preserved for new data")
                return True
            else:
                print(f"  WARNING: {remaining} records still remain after clearing!")
                return False

    except Exception as e:
        print(f" ERROR: Failed to clear database: {e}")
        if not dry_run:
            try:
                db.session.rollback()
                print("🔄 Database transaction rolled back")
            except:
                pass
        return False

def get_confirmation():
    """Get user confirmation before proceeding"""
    print("\n" + "="*60)
    print("🗑️  DATABASE CLEARING CONFIRMATION")
    print("="*60)
    print("This will PERMANENTLY DELETE all data from your database!")
    print("This includes:")
    print("  • All user accounts and profiles")
    print("  • All projects and tasks")
    print("  • All saved content and bookmarks")
    print("  • All feedback and analysis data")
    print("  • All recommendation history")
    print()
    print("  This action CANNOT be undone!")
    print("="*60)

    while True:
        response = input("\nType 'YES' to confirm deletion: ").strip().upper()
        if response == 'YES':
            return True
        elif response.lower() in ['no', 'cancel', 'quit', 'exit']:
            print(" Operation cancelled")
            return False
        else:
            print("Please type 'YES' to confirm or 'no' to cancel")

def main():
    parser = argparse.ArgumentParser(description='Clear all data from Fuze database')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt (dangerous!)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')

    args = parser.parse_args()

    print("🗑️  Fuze Database Clearing Script")
    print("="*40)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will actually be deleted")
    elif not args.force:
        if not get_confirmation():
            return False

    success = clear_all_data(dry_run=args.dry_run)

    if success:
        if args.dry_run:
            print("\n🔍 Dry run completed successfully!")
        else:
            print("\n🎉 Database clearing completed successfully!")
            print("   You can now test Fuze with a fresh database state.")
        return True
    else:
        print("\n💥 Database clearing failed!")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
