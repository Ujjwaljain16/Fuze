import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, SavedContent
from blueprints.recommendations import get_enhanced_recommendations

def test_phase2_direct():
    """Test Phase 2 directly without Flask context"""
    print("🧪 Testing Phase 2 (Power Boost) Directly")
    print("=" * 50)
    
    # Create a minimal Flask app context
    app = Flask(__name__)
    
    # Use the same database as the main app
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///fuze.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    print(f"🔗 Using database: {database_url}")
    
    # Use existing database instance
    with app.app_context():
        # Database is already initialized from models import
        pass
    
    with app.app_context():
        # Initialize database
        db.init_app(app)
        
        # Test data
        test_data = {
            "project_title": "Learning Project",
            "project_description": "I want to learn and improve my skills",
            "technologies": "mobile app react native expo",
            "learning_goals": "Master relevant technologies and improve skills",
            "content_type": "all",
            "difficulty": "all",
            "max_recommendations": 10
        }
        
        # Get user ID (assuming user 1 exists)
        user_id = 1
        
        print(f"📊 Test Data: {test_data}")
        print(f"👤 User ID: {user_id}")
        print()
        
        try:
            # Call Phase 2 directly
            print("🚀 Calling Phase 2 (Power Boost)...")
            result = get_enhanced_recommendations(user_id, test_data)
            
            print(f"✅ Phase 2 Result: {result}")
            
            if result and 'recommendations' in result:
                recommendations = result['recommendations']
                print(f"📈 Found {len(recommendations)} recommendations")
                
                for i, rec in enumerate(recommendations[:5], 1):
                    print(f"{i}. {rec.get('title', 'No title')}")
                    print(f"   Score: {rec.get('score', 'N/A')}")
                    print(f"   Algorithm: {rec.get('algorithm_used', 'N/A')}")
                    print()
            else:
                print("❌ No recommendations returned")
                
        except Exception as e:
            print(f"❌ Error in Phase 2: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_phase2_direct() 