import urllib.request
import json

url = "https://huggingface.co/api/spaces/Ujjwaljain16/fuze-backend"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Space Status: {data.get('runtime', {}).get('stage')}")
        print(f"Hardware: {data.get('runtime', {}).get('hardware')}")
except Exception as e:
    print(f"Error fetching space status: {e}")
