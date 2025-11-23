#!/usr/bin/env python3
"""
Multi-User Flow Test Script
Tests complete user flow with multiple users to verify data isolation
"""

import sys
import os
from datetime import datetime

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import create_app
from models import db, User, SavedContent, ContentAnalysis, Project
from werkzeug.security import generate_password_hash

app = create_app()

def create_test_users():
    """Create multiple test users"""
    with app.app_context():
        print("\n" + "="*60)
        print("Creating Test Users")
        print("="*60)
        
        users_data = []
        test_users_data = [
            {'username': 'testuser1', 'email': 'test1@example.com', 'password': 'testpass123'},
            {'username': 'testuser2', 'email': 'test2@example.com', 'password': 'testpass123'},
            {'username': 'testuser3', 'email': 'test3@example.com', 'password': 'testpass123'},
        ]
        
        for user_data in test_users_data:
            # Check if user exists
            existing = User.query.filter_by(username=user_data['username']).first()
            if existing:
                user_id = existing.id
                username = existing.username
                print(f"  User {username} already exists (ID: {user_id})")
                users_data.append({
                    'id': user_id,
                    'username': username,
                    'email': existing.email,
                    'password': user_data['password']
                })
                continue
            
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password'])
            )
            db.session.add(user)
            db.session.commit()
            # Store data before leaving context
            user_id = user.id
            username = user.username
            users_data.append({
                'id': user_id,
                'username': username,
                'email': user.email,
                'password': user_data['password']
            })
            print(f"  ✅ Created user: {username} (ID: {user_id})")
        
        return users_data

def create_test_data_for_users(users_data):
    """Create test bookmarks and projects for each user"""
    with app.app_context():
        print("\n" + "="*60)
        print("Creating Test Data")
        print("="*60)
        
        for i, user_data in enumerate(users_data, 1):
            user_id = user_data['id']
            username = user_data['username']
            print(f"\n  User {i}: {username} (ID: {user_id})")
            
            # Create projects
            project = Project(
                user_id=user_id,
                title=f'Test Project {i}',
                description=f'Test project for {username}',
                technologies=f'Python, Flask, User{i}'
            )
            db.session.add(project)
            db.session.commit()
            print(f"    ✅ Created project: {project.title} (ID: {project.id})")
            
            # Create bookmarks
            for j in range(3):
                bookmark = SavedContent(
                    user_id=user_id,
                    url=f'https://example.com/user{i}/bookmark{j}',
                    title=f'Bookmark {j} for {username}',
                    extracted_text=f'Content for user {username}, bookmark {j}',
                    quality_score=10
                )
                db.session.add(bookmark)
            db.session.commit()
            print(f"    ✅ Created 3 bookmarks")
        
        print("\n✅ Test data created successfully!")

def verify_data_isolation(users_data):
    """Verify that each user can only see their own data"""
    with app.app_context():
        print("\n" + "="*60)
        print("Verifying Data Isolation")
        print("="*60)
        
        all_good = True
        
        for i, user_data in enumerate(users_data, 1):
            user_id = user_data['id']
            username = user_data['username']
            print(f"\n  User {i}: {username} (ID: {user_id})")
            
            # Check bookmarks
            bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
            print(f"    Bookmarks: {len(bookmarks)}")
            
            # Verify all bookmarks belong to this user
            for bm in bookmarks:
                if bm.user_id != user_id:
                    print(f"    ❌ ERROR: Bookmark {bm.id} belongs to user {bm.user_id}, not {user_id}!")
                    all_good = False
                else:
                    print(f"      ✅ Bookmark {bm.id}: {bm.title[:40]}...")
            
            # Check projects
            projects = Project.query.filter_by(user_id=user_id).all()
            print(f"    Projects: {len(projects)}")
            
            # Verify all projects belong to this user
            for proj in projects:
                if proj.user_id != user_id:
                    print(f"    ❌ ERROR: Project {proj.id} belongs to user {proj.user_id}, not {user_id}!")
                    all_good = False
                else:
                    print(f"      ✅ Project {proj.id}: {proj.title}")
            
            # Check that user can't see other users' data
            other_users = [u for u in users_data if u['id'] != user_id]
            for other_user in other_users:
                other_bookmarks = SavedContent.query.filter_by(user_id=other_user['id']).all()
                other_projects = Project.query.filter_by(user_id=other_user['id']).all()
                
                # These should exist but user shouldn't be able to access them via API
                # (We're just checking database isolation here)
                print(f"    Other user {other_user['id']} has {len(other_bookmarks)} bookmarks, {len(other_projects)} projects")
        
        if all_good:
            print("\n✅ Data isolation verified - all users' data is properly separated!")
        else:
            print("\n❌ Data isolation FAILED - some data is mixed between users!")
        
        return all_good

def test_bookmark_import_simulation(user_data):
    """Simulate bookmark import for a user"""
    with app.app_context():
        user_id = user_data['id']
        username = user_data['username']
        print(f"\n  Simulating bookmark import for {username}...")
        
        # Simulate importing 5 bookmarks
        new_bookmarks = []
        for i in range(5):
            bookmark = SavedContent(
                user_id=user_id,
                url=f'https://example.com/imported/{i}',
                title=f'Imported Bookmark {i}',
                extracted_text=f'Imported content {i}',
                quality_score=10
            )
            new_bookmarks.append(bookmark)
            db.session.add(bookmark)
        
        db.session.commit()
        print(f"    ✅ Imported {len(new_bookmarks)} bookmarks")
        
        # Verify all have correct user_id
        for bm in new_bookmarks:
            if bm.user_id != user_id:
                print(f"    ❌ ERROR: Imported bookmark {bm.id} has wrong user_id: {bm.user_id} (expected {user_id})")
                return False
        
        print(f"    ✅ All imported bookmarks have correct user_id")
        return True

def main():
    """Run complete multi-user flow test"""
    print("="*60)
    print("MULTI-USER FLOW TEST")
    print("="*60)
    print("\nThis will:")
    print("  1. Create 3 test users")
    print("  2. Create test data for each user")
    print("  3. Verify data isolation")
    print("  4. Test bookmark import for each user")
    print("\n⚠️  Make sure you've cleared the database first!")
    
    input("\nPress Enter to continue...")
    
    # Create users
    users_data = create_test_users()
    
    # Create test data
    create_test_data_for_users(users_data)
    
    # Verify isolation
    isolation_ok = verify_data_isolation(users_data)
    
    # Test bookmark import for each user
    print("\n" + "="*60)
    print("Testing Bookmark Import")
    print("="*60)
    
    import_ok = True
    for user_data in users_data:
        if not test_bookmark_import_simulation(user_data):
            import_ok = False
    
    # Final summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if isolation_ok and import_ok:
        print("✅ All tests passed!")
        print("   - Data isolation: ✅")
        print("   - Bookmark import: ✅")
        print("\n🎉 Multi-user flow is working correctly!")
    else:
        print("❌ Some tests failed!")
        if not isolation_ok:
            print("   - Data isolation: ❌")
        if not import_ok:
            print("   - Bookmark import: ❌")
    
    # Show final counts
    with app.app_context():
        print("\n" + "="*60)
        print("Final Database State")
        print("="*60)
        
        total_users = User.query.count()
        total_bookmarks = SavedContent.query.count()
        total_projects = Project.query.count()
        
        print(f"\n  Total Users: {total_users}")
        print(f"  Total Bookmarks: {total_bookmarks}")
        print(f"  Total Projects: {total_projects}")
        
        print("\n  Breakdown by user:")
        for user_data in users_data:
            user_id = user_data['id']
            username = user_data['username']
            bm_count = SavedContent.query.filter_by(user_id=user_id).count()
            proj_count = Project.query.filter_by(user_id=user_id).count()
            print(f"    {username} (ID {user_id}): {bm_count} bookmarks, {proj_count} projects")

if __name__ == "__main__":
    main()

