import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print(f"Checking API Health at {BASE_URL}/ ...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")

def test_chat():
    print(f"\nTesting Chat Endpoint at {BASE_URL}/chat ...")
    payload = {
        "session_id": "test_script_session",
        "message": "Hello friend, I have a business proposal for you about a lottery.",
        "sender": "scammer"
    }
    
    try:
        start_time = time.time()
        print(f"Sending message: {payload['message']}")
        response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
        end_time = time.time()
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response Time: {end_time - start_time:.2f}s")
            print(f"API Response: {data.get('response')}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Chat test failed: {e}")

if __name__ == "__main__":
    test_health()
    test_chat()
