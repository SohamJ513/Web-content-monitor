# backend/test_db.py
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from app.database import create_user, get_user_by_email, is_db_available
    
    if not is_db_available():
        print("❌ MongoDB client is not available")
    else:
        print("✅ MongoDB connection is ready!")
        
        # Test user creation
        test_user = {
            "email": "test@example.com",
            "password": "testpassword"
        }

        user = create_user(test_user)
        if user:
            print(f"✅ User created: {user['email']}")
            print(f"✅ User ID: {user['_id']}")
            
            # Test retrieving user
            retrieved_user = get_user_by_email("test@example.com")
            if retrieved_user:
                print(f"✅ User retrieved: {retrieved_user['email']}")
                print(f"✅ User ID: {retrieved_user['_id']}")
            else:
                print("❌ User not found")
        else:
            print("❌ User creation failed (might already exist)")

except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()