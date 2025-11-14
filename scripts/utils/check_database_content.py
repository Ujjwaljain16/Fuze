#!/usr/bin/env python3
"""
Check Database Content
See what's actually stored in the database that's causing weird recommendations
"""
import os
import sys
from app import app, db
from models import SavedContent, User, Project

def check_database_content():
    """Check what content is in the database"""
    print("🔍 Database Content Analysis")
    print("=" * 40)
    
    with app.app_context():
        # Check all saved content
        print("\n📚 All Saved Content:")
        print("-" * 30)
        
        all_content = SavedContent.query.all()
        print(f"Total saved content: {len(all_content)}")
        
        for i, content in enumerate(all_content[:10]):  # Show first 10
            print(f"\n{i+1}. ID: {content.id}")
            print(f"   Title: {content.title}")
            print(f"   URL: {content.url}")
            print(f"   User ID: {content.user_id}")
            print(f"   Quality Score: {content.quality_score}")
            print(f"   Has Embedding: {content.embedding is not None}")
            print(f"   Extracted Text Length: {len(content.extracted_text) if content.extracted_text else 0}")
            
            # Show first 100 chars of extracted text
            if content.extracted_text:
                preview = content.extracted_text[:100].replace('\n', ' ')
                print(f"   Text Preview: {preview}...")
        
        # Check users
        print("\n👥 Users:")
        print("-" * 15)
        users = User.query.all()
        for user in users:
            print(f"   User ID: {user.id}, Username: {user.username}")
        
        # Check projects
        print("\n📁 Projects:")
        print("-" * 15)
        projects = Project.query.all()
        for project in projects:
            print(f"   Project ID: {project.id}, Title: {project.title}")
        
        # Check for test data specifically
        print("\n🧪 Test Data Check:")
        print("-" * 20)
        test_content = SavedContent.query.filter(
            SavedContent.title.like('%test%') | 
            SavedContent.title.like('%Test%') |
            SavedContent.title.like('%example%') |
            SavedContent.title.like('%Example%')
        ).all()
        
        if test_content:
            print(f"Found {len(test_content)} items with 'test' or 'example' in title:")
            for content in test_content:
                print(f"   - {content.title} (ID: {content.id})")
        else:
            print("No obvious test data found in titles")
        
        # Check for dictionary content
        print("\n📖 Dictionary Content Check:")
        print("-" * 25)
        dict_content = SavedContent.query.filter(
            SavedContent.title.like('%Dictionary%') |
            SavedContent.title.like('%dictionary%') |
            SavedContent.title.like('%International%')
        ).all()
        
        if dict_content:
            print(f"Found {len(dict_content)} dictionary-related items:")
            for content in dict_content:
                print(f"   - {content.title} (ID: {content.id})")
        else:
            print("No dictionary content found")

if __name__ == "__main__":
    check_database_content() 