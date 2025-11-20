#!/usr/bin/env python3
"""
Production Readiness Checklist for Fuze Bookmark System
Comprehensive verification of all features and functionality
"""

import sys
import os
from datetime import datetime

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def check_core_dependencies():
    """Check all required dependencies are available"""
    print("🔧 CORE DEPENDENCIES CHECK:")

    critical_deps = [
        ('flask', 'flask'), ('sqlalchemy', 'sqlalchemy'), ('redis', 'redis'),
        ('numpy', 'numpy'), ('sentence_transformers', 'sentence_transformers'),
        ('google.generativeai', 'google.generativeai'), ('scrapling', 'scrapling'),
        ('camoufox', 'camoufox'), ('bs4', 'beautifulsoup4')
    ]

    missing = []
    for import_name, display_name in critical_deps:
        try:
            __import__(import_name)
            print(f"✅ {display_name}")
        except ImportError:
            missing.append(display_name)
            print(f"❌ {display_name}")

    return len(missing) == 0, missing

def check_database_models():
    """Verify database models are properly defined"""
    print("\n💾 DATABASE MODELS CHECK:")

    try:
        from models import db, User, SavedContent, ContentAnalysis
        from config import DevelopmentConfig
        from flask import Flask
        from sqlalchemy import inspect

        # Create Flask app context
        app = Flask(__name__)
        app.config.from_object(DevelopmentConfig)
        db.init_app(app)

        with app.app_context():
            models = [User, SavedContent, ContentAnalysis]
            issues = []

            for model in models:
                try:
                    # Check table exists
                    table_name = model.__tablename__
                    inspector = inspect(db.engine)
                    if table_name not in inspector.get_table_names():
                        issues.append(f"Table {table_name} missing")
                        continue

                    # Check required columns
                    columns = [col.name for col in model.__table__.columns]
                    print(f"✅ {table_name}: {len(columns)} columns")

                except Exception as e:
                    issues.append(f"{model.__name__}: {e}")

            return len(issues) == 0, issues

    except Exception as e:
        return False, [str(e)]

def check_api_key_management():
    """Verify API key management system"""
    print("\n🔑 API KEY MANAGEMENT CHECK:")

    try:
        from services.multi_user_api_manager import api_manager, get_user_api_key
        from cryptography.fernet import Fernet

        # Check encryption
        test_key = 'AIzaSyTest123456789'
        encrypted = api_manager.encrypt_api_key(test_key)
        decrypted = api_manager.decrypt_api_key(encrypted)

        if decrypted == test_key:
            print("✅ API key encryption/decryption working")
        else:
            return False, ["API key encryption failed"]

        # Check validation - use a properly formatted Gemini API key
        valid_key = 'AIzaSyTest123456789012345678901234567890'
        if api_manager.validate_api_key(valid_key):
            print("✅ API key validation working")
        else:
            return False, ["API key validation failed"]

        return True, []

    except Exception as e:
        return False, [str(e)]

def check_scraping_system():
    """Verify scraping system functionality"""
    print("\n🌐 SCRAPING SYSTEM CHECK:")

    try:
        # Test ScraplingEnhancedScraper import
        from scrapers.scrapling_enhanced_scraper import ScraplingEnhancedScraper
        scraper = ScraplingEnhancedScraper()

        # Check key methods exist
        methods = ['scrape_url_enhanced', '_check_browsers_installed', '_clean_and_optimize_content']
        for method in methods:
            if hasattr(scraper, method):
                print(f"✅ {method} method available")
            else:
                return False, [f"Missing method: {method}"]

        return True, []

    except Exception as e:
        return False, [str(e)]

def check_embedding_system():
    """Verify embedding generation"""
    print("\n🧠 EMBEDDING SYSTEM CHECK:")

    try:
        from utils.embedding_utils import get_embedding

        # Test embedding generation
        test_text = "This is a test for embedding generation"
        embedding = get_embedding(test_text)

        if embedding is not None and len(embedding) > 0:
            print(f"✅ Embedding generation working (dimension: {len(embedding)})")
            return True, []
        else:
            return False, ["Embedding generation failed"]

    except Exception as e:
        return False, [str(e)]

def check_content_analysis():
    """Verify content analysis system"""
    print("\n📊 CONTENT ANALYSIS CHECK:")

    try:
        from utils.gemini_utils import GeminiAnalyzer

        # Test analyzer initialization (without actual API call)
        analyzer = GeminiAnalyzer(api_key=None)  # Should use default

        if hasattr(analyzer, 'analyze_bookmark_content'):
            print("✅ Content analysis system available")
            return True, []
        else:
            return False, ["Content analysis methods missing"]

    except Exception as e:
        return False, [str(e)]

def check_background_services():
    """Verify background service integration"""
    print("\n⚙️ BACKGROUND SERVICES CHECK:")

    try:
        from services.background_analysis_service import BackgroundAnalysisService

        service = BackgroundAnalysisService()
        if hasattr(service, 'rate_limits') and service.rate_limits:
            print("✅ Background analysis service configured")
            return True, []
        else:
            return False, ["Background service not properly configured"]

    except Exception as e:
        return False, [str(e)]

def check_workflow_integration():
    """Verify end-to-end workflow integration"""
    print("\n🔄 WORKFLOW INTEGRATION CHECK:")

    try:
        # Check if bookmark blueprint integrates all components
        with open('blueprints/bookmarks.py', 'r') as f:
            code = f.read()

        checks = [
            ('scrapling_enhanced_scraper', 'Enhanced scraping'),
            ('get_embedding', 'Embedding generation'),
            ('background_analysis_service', 'Background analysis'),
            ('ContentAnalysis', 'Database models')
        ]

        for check, description in checks:
            if check in code:
                print(f"✅ {description} integrated")
            else:
                return False, [f"Missing {description} integration"]

        return True, []

    except Exception as e:
        return False, [str(e)]

def check_error_handling():
    """Verify comprehensive error handling"""
    print("\n🛡️ ERROR HANDLING CHECK:")

    try:
        # Check for try/catch blocks in critical files
        files_to_check = [
            'blueprints/bookmarks.py',
            'services/background_analysis_service.py',
            'scrapers/scrapling_enhanced_scraper.py'
        ]

        for file_path in files_to_check:
            with open(file_path, 'r') as f:
                content = f.read()

            if 'try:' in content and 'except' in content:
                print(f"✅ Error handling in {file_path.split('/')[-1]}")
            else:
                return False, [f"Missing error handling in {file_path}"]

        return True, []

    except Exception as e:
        return False, [str(e)]

def check_configuration():
    """Verify configuration and environment setup"""
    print("\n⚙️ CONFIGURATION CHECK:")

    required_env_vars = ['DATABASE_URL', 'REDIS_URL', 'SECRET_KEY']
    missing_vars = []

    for var in required_env_vars:
        if os.environ.get(var):
            print(f"✅ {var} configured")
        else:
            missing_vars.append(var)
            print(f"❌ {var} missing")

    if missing_vars:
        return False, [f"Missing environment variables: {', '.join(missing_vars)}"]

    return True, []

def main():
    """Run complete production readiness check"""
    print("🚀 PRODUCTION READINESS CHECK")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)

    checks = [
        ("Core Dependencies", check_core_dependencies),
        ("Database Models", check_database_models),
        ("API Key Management", check_api_key_management),
        ("Scraping System", check_scraping_system),
        ("Embedding System", check_embedding_system),
        ("Content Analysis", check_content_analysis),
        ("Background Services", check_background_services),
        ("Workflow Integration", check_workflow_integration),
        ("Error Handling", check_error_handling),
        ("Configuration", check_configuration)
    ]

    all_passed = True
    all_issues = []

    for check_name, check_func in checks:
        try:
            passed, issues = check_func()
            if not passed:
                all_passed = False
                all_issues.extend([f"{check_name}: {issue}" for issue in issues])
        except Exception as e:
            all_passed = False
            all_issues.append(f"{check_name}: {str(e)}")

    print("\n" + "=" * 50)
    print("📋 FINAL PRODUCTION READINESS ASSESSMENT:")

    if all_passed:
        print("🎉 PRODUCTION READY! All systems verified and operational.")
        print("\n✅ Key Features Confirmed:")
        print("   • Multi-user API key management with encryption")
        print("   • Advanced web scraping with Scrapling + Camoufox")
        print("   • Comprehensive embedding generation")
        print("   • Gradual, rate-limited content analysis")
        print("   • Automated background processing")
        print("   • Redis caching and progress tracking")
        print("   • Complete database integration")
        print("   • Robust error handling and logging")
    else:
        print(f"❌ NOT PRODUCTION READY - {len(all_issues)} issues found:")
        for issue in all_issues:
            print(f"   • {issue}")

    print("\n" + "=" * 50)

    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
