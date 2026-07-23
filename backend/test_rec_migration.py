import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5000/api"

def login():
    # Register first just in case
    import time
    username = f"test_{int(time.time())}"
    email = f"{username}@example.com"
    
    requests.post(f"{BASE_URL}/auth/register", json={
        "username": username,
        "email": email,
        "password": "Password123!"
    })
    
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    return res.json().get('access_token')

def get_bookmarks(token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/bookmarks", headers=headers)
    return res.json().get('bookmarks', [])

def test_endpoints():
    token = login()
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get a bookmark ID to test with
    bookmarks = get_bookmarks(token)
    if not bookmarks:
        logger.error("No bookmarks found, cannot test feedback endpoint.")
        # Try to test the others anyway
        content_id = 1
    else:
        content_id = bookmarks[0]['id']
    
    # 1. Test POST /feedback
    logger.info("Testing POST /api/recommendations/feedback")
    fb_resp = requests.post(f'{BASE_URL}/recommendations/feedback', json={
        'recommendation_id': content_id,
        'feedback_type': 'positive',
        'feedback_data': {'topic': 'python'}
    }, headers=headers)
    
    if fb_resp.status_code == 200:
        logger.info("✅ POST /feedback successful")
    else:
        logger.error(f"❌ POST /feedback failed: {fb_resp.text}")
        
    # 2. Test GET /user-preferences
    logger.info("Testing GET /api/recommendations/user-preferences")
    pref_resp = requests.get(f'{BASE_URL}/recommendations/user-preferences', headers=headers)
    
    if pref_resp.status_code == 200:
        data = pref_resp.json()
        logger.info("✅ GET /user-preferences successful")
        logger.info(f"   Data keys: {list(data.keys())}")
    else:
        logger.error(f"❌ GET /user-preferences failed: {pref_resp.text}")
        
    # 3. Test GET /learning-insights
    logger.info("Testing GET /api/recommendations/learning-insights")
    insights_resp = requests.get(f'{BASE_URL}/recommendations/learning-insights', headers=headers)
    
    if insights_resp.status_code == 200:
        data = insights_resp.json()
        logger.info("✅ GET /learning-insights successful")
        logger.info(f"   Data keys: {list(data.keys())}")
    else:
        logger.error(f"❌ GET /learning-insights failed: {insights_resp.text}")
        
    # 4. Test GET /analysis/stats
    logger.info("Testing GET /api/recommendations/analysis/stats")
    stats_resp = requests.get(f'{BASE_URL}/recommendations/analysis/stats', headers=headers)
    
    if stats_resp.status_code == 200:
        data = stats_resp.json()
        logger.info("✅ GET /analysis/stats successful")
        logger.info(f"   Data keys: {list(data.keys())}")
    else:
        logger.error(f"❌ GET /analysis/stats failed: {stats_resp.text}")

if __name__ == '__main__':
    test_endpoints()
