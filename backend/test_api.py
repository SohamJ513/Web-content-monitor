# backend/test_api.py
import requests
import json
import random
import string

BASE_URL = "http://localhost:8000"

def generate_random_email():
    """Generate a random email for testing"""
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_string}@example.com"

def test_api():
    print("🚀 Testing FreshLense API")
    print("=" * 50)
    
    # Generate unique test email
    test_email = generate_random_email()
    test_password = "testpassword123"
    
    # Test health endpoint
    print("1. Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"   Status: {response.status_code}, Response: {response.json()}")
    
    # Test registration with new email
    print(f"\n2. Testing user registration with email: {test_email}")
    user_data = {
        "email": test_email,
        "password": test_password
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✅ Registration successful! User: {response.json()}")
    else:
        print(f"   ❌ Registration failed: {response.json()}")
        # Try login in case user already exists
        print(f"   🔄 Trying login instead...")
    
    # Test login
    print(f"\n3. Testing user login with email: {test_email}")
    login_data = {
        "username": test_email,
        "password": test_password
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"   ✅ Login successful! Token: {token[:50]}...")
        
        # Test authenticated endpoints
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\n4. Testing tracked pages endpoint...")
        response = requests.get(f"{BASE_URL}/api/pages", headers=headers)
        print(f"   Status: {response.status_code}")
        
        try:
            pages = response.json()
            print(f"   Found {len(pages)} pages")
        except:
            print(f"   Response: {response.text}")
        
        # Test creating a page
        print("\n5. Testing page creation...")
        page_data = {
            "url": "https://httpbin.org/html",
            "display_name": "Test HTTPBin Page",
            "check_interval_minutes": 5
        }
        response = requests.post(f"{BASE_URL}/api/pages", json=page_data, headers=headers)
        print(f"   Status: {response.status_code}")
        
        try:
            if response.status_code == 200:
                page_info = response.json()
                print(f"   ✅ Page created successfully!")
                print(f"   Page ID: {page_info.get('id', 'N/A')}")
                print(f"   Page URL: {page_info.get('url', 'N/A')}")
            else:
                error_info = response.json()
                print(f"   ❌ Page creation failed: {error_info}")
        except json.JSONDecodeError:
            print(f"   ❌ Server error (non-JSON response): {response.text}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
        
        # Test getting the page we just created
        if response.status_code == 200:
            print("\n6. Testing get page endpoint...")
            page_id = response.json().get('id')
            if page_id:
                response = requests.get(f"{BASE_URL}/api/pages/{page_id}", headers=headers)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    print(f"   ✅ Page retrieved successfully!")
                else:
                    print(f"   ❌ Page retrieval failed: {response.json()}")
        
    else:
        print(f"   ❌ Login failed: {response.json()}")
    
    print("\n" + "=" * 50)
    print("✅ API test completed!")

if __name__ == "__main__":
    test_api()