# backend/test_scheduler.py
import sys
import os
import time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scheduler import MonitoringScheduler
from app.database import create_tracked_page, get_tracked_pages

def test_scheduler():
    print("🚀 Testing Monitoring Scheduler")
    print("=" * 50)
    
    # Create a test page to monitor
    test_page = {
        "url": "https://httpbin.org/html",
        "display_name": "HTTPBin Test Page",
        "check_interval_minutes": 2  # Check every 2 minutes for testing
    }
    
    # Create the page in database (using a test user ID)
    test_user_id = "000000000000000000000000"  # Dummy ID for testing
    page = create_tracked_page(test_page, test_user_id)
    
    if not page:
        print("❌ Failed to create test page")
        return
        
    print(f"✅ Created test page: {page['url']} (ID: {page['_id']})")
    
    # Initialize and start scheduler
    scheduler = MonitoringScheduler()
    scheduler.start()
    
    print("\n📋 Scheduled jobs:")
    for job in scheduler.get_scheduled_jobs():
        print(f"   - {job.name} (every {job.trigger.interval_length / 60} minutes)")
    
    print(f"\n⏰ Scheduler started at {datetime.now()}")
    print("📊 Monitoring will run in the background")
    print("💡 Press Ctrl+C to stop the scheduler")
    
    try:
        # Let the scheduler run for a while
        for i in range(5):
            time.sleep(30)  # Check every 30 seconds
            print(f"⏳ Still running... ({i * 30}s elapsed)")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping scheduler...")
    
    finally:
        scheduler.shutdown()
        print("✅ Test completed")

if __name__ == "__main__":
    test_scheduler()