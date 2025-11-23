#!/usr/bin/env python3
"""
Quick script to verify production data is still intact after running tests
"""

import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import create_app
from models import db, User, SavedContent, Project

app = create_app()

with app.app_context():
    print("="*60)
    print("Verifying Production Data")
    print("="*60)
    
    # Check test users
    test_users = User.query.filter(User.username.in_(['testuser1', 'testuser2', 'testuser3'])).all()
    
    print(f"\n✅ Found {len(test_users)} test users:")
    for user in test_users:
        bm_count = SavedContent.query.filter_by(user_id=user.id).count()
        proj_count = Project.query.filter_by(user_id=user.id).count()
        print(f"   {user.username} (ID {user.id}): {bm_count} bookmarks, {proj_count} projects")
    
    # Total counts
    total_users = User.query.count()
    total_bookmarks = SavedContent.query.count()
    total_projects = Project.query.count()
    
    print(f"\n📊 Total Database State:")
    print(f"   Users: {total_users}")
    print(f"   Bookmarks: {total_bookmarks}")
    print(f"   Projects: {total_projects}")
    
    if len(test_users) == 3:
        print("\n✅ Production data is INTACT - tests did NOT clear the database!")
    else:
        print(f"\n⚠️  Expected 3 test users, found {len(test_users)}")

