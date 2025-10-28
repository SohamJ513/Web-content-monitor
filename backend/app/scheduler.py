from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime
import os
from bson import ObjectId
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = None
db = None

try:
    client = MongoClient(MONGO_URI)
    client.admin.command('ping')  # Test the connection
    print("✅ MongoDB connection successful!")
    db = client['freshlense']

    # Collections
    users_collection = db['users']
    pages_collection = db['tracked_pages']
    versions_collection = db['page_versions']
    changes_collection = db['change_logs']

    # Indexes
    def create_indexes():
        users_collection.create_index([("email", ASCENDING)], unique=True)
        pages_collection.create_index([("user_id", ASCENDING), ("url", ASCENDING)], unique=True)
        pages_collection.create_index([("user_id", ASCENDING), ("is_active", ASCENDING)])
        versions_collection.create_index([("page_id", ASCENDING), ("timestamp", DESCENDING)])
        changes_collection.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
        changes_collection.create_index([("page_id", ASCENDING), ("timestamp", DESCENDING)])
        print("✅ Database indexes created successfully!")

    create_indexes()

except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print(f"❌ MongoDB connection failed: {e}")
    client = None
    db = None


# ---------------- Helper ----------------
def is_db_available():
    return db is not None


def doc_to_dict(doc):
    """Convert MongoDB ObjectIds -> str recursively"""
    if doc is None:
        return None
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    for key, value in list(doc.items()):
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, dict):
            doc[key] = doc_to_dict(value)
        elif isinstance(value, list):
            doc[key] = [doc_to_dict(v) if isinstance(v, dict) else str(v) if isinstance(v, ObjectId) else v for v in value]
    return doc


# ---------------- User ----------------
def get_user_by_email(email: str):
    """Get user by email address"""
    if db is None:
        return None
    user = users_collection.find_one({"email": email})
    return user  # Return raw doc (main.py expects ObjectId format)


def create_user(user_data: dict):
    """Create a new user with hashed password"""
    if db is None:
        return None
    hashed_password = pwd_context.hash(user_data['password'])
    user_doc = {
        "email": user_data['email'],
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow(),
        "notification_preferences": {
            "email_alerts": True,
            "frequency": "immediately"
        }
    }
    try:
        result = users_collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        return user_doc  # Return with ObjectId for main.py normalize_doc
    except DuplicateKeyError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------- Tracked Pages ----------------
def get_tracked_pages(user_id, active_only: bool = True):
    """Get all tracked pages for a user"""
    if db is None:
        return []
    
    # Handle both ObjectId and string user_id
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
    query = {"user_id": user_id}
    if active_only:
        query["is_active"] = True
    pages = pages_collection.find(query).sort("created_at", DESCENDING)
    return list(pages)  # Return raw docs for main.py normalize_doc


def get_tracked_page(page_id: str):
    """Get a single tracked page by ID"""
    if db is None:
        return None
    try:
        page = pages_collection.find_one({"_id": ObjectId(page_id)})
        return page  # Return raw doc
    except:
        return None


def create_tracked_page(page_data: dict, user_id):
    """Create a new tracked page"""
    if db is None:
        return None
    
    # Handle both ObjectId and string user_id
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
    page_doc = {
        "user_id": user_id,
        "url": page_data["url"],
        "display_name": page_data.get("display_name") or page_data["url"],
        "check_interval_minutes": page_data.get("check_interval_minutes", 1440),
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_checked": None,
        "last_change_detected": None,
        "current_version_id": None,
    }
    try:
        result = pages_collection.insert_one(page_doc)
        page_doc["_id"] = result.inserted_id
        return page_doc  # Return raw doc for main.py normalize_doc
    except DuplicateKeyError:
        return None


def update_tracked_page(page_id: str, update_data: dict) -> bool:
    """Update a tracked page"""
    if db is None:
        return False
    
    # Handle ObjectId conversion for current_version_id
    update_data_copy = update_data.copy()
    if "current_version_id" in update_data_copy and isinstance(update_data_copy["current_version_id"], str):
        update_data_copy["current_version_id"] = ObjectId(update_data_copy["current_version_id"])
    
    try:
        result = pages_collection.update_one({"_id": ObjectId(page_id)}, {"$set": update_data_copy})
        return result.modified_count > 0
    except:
        return False


def delete_tracked_page(page_id: str) -> bool:
    """Delete a tracked page by ID"""
    if db is None:
        return False
    try:
        result = pages_collection.delete_one({"_id": ObjectId(page_id)})
        return result.deleted_count > 0
    except:
        return False


# ---------------- Page Versions ----------------
def create_page_version(page_id: str, text_content: str, url: str):
    """Create a new page version"""
    if db is None:
        return None
    
    version = {
        "page_id": ObjectId(page_id),
        "timestamp": datetime.utcnow(),
        "text_content": text_content,
        "metadata": {
            "url": url,
            "content_length": len(text_content),
            "word_count": len(text_content.split()) if text_content else 0,
            "fetched_at": datetime.utcnow().isoformat(),
        },
    }
    try:
        result = versions_collection.insert_one(version)
        version["_id"] = result.inserted_id
        return version  # Return raw doc for main.py normalize_doc
    except:
        return None


def get_page_versions(page_id: str, limit: int = 10):
    """Get page versions for a specific page"""
    if db is None:
        return []
    try:
        versions = versions_collection.find({"page_id": ObjectId(page_id)}).sort("timestamp", DESCENDING).limit(limit)
        return list(versions)  # Return raw docs for main.py normalize_doc
    except:
        return []


# ---------------- Change Logs ----------------
def create_change_log(change_data: dict):
    """Create a new change log entry"""
    if db is None:
        return None
    
    change_data_copy = change_data.copy()
    
    # Handle ObjectId conversion
    if "page_id" in change_data_copy and isinstance(change_data_copy["page_id"], str):
        change_data_copy["page_id"] = ObjectId(change_data_copy["page_id"])
    if "user_id" in change_data_copy and isinstance(change_data_copy["user_id"], str):
        change_data_copy["user_id"] = ObjectId(change_data_copy["user_id"])
    
    # Ensure timestamp is set
    if "timestamp" not in change_data_copy:
        change_data_copy["timestamp"] = datetime.utcnow()
    
    try:
        result = changes_collection.insert_one(change_data_copy)
        return str(result.inserted_id)
    except:
        return None


def get_change_logs_for_page(page_id: str, limit: int = 20):
    """Get change logs for a specific page"""
    if db is None:
        return []
    try:
        changes = changes_collection.find({"page_id": ObjectId(page_id)}).sort("timestamp", DESCENDING).limit(limit)
        return list(changes)  # Return raw docs for main.py normalize_doc
    except:
        return []


def get_change_logs_for_user(user_id, limit: int = 20):
    """Get change logs for a specific user"""
    if db is None:
        return []
    
    # Handle both ObjectId and string user_id
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    
    try:
        changes = changes_collection.find({"user_id": user_id}).sort("timestamp", DESCENDING).limit(limit)
        return list(changes)  # Return raw docs for main.py normalize_doc
    except:
        return []


# ---------------- Additional utility functions for scheduler ----------------
def get_all_active_pages():
    """Get all active pages across all users (for scheduler)"""
    if db is None:
        return []
    try:
        pages = pages_collection.find({"is_active": True})
        return list(pages)
    except:
        return []


def get_pages_due_for_check():
    """Get pages that are due for checking based on their interval"""
    if db is None:
        return []
    try:
        # Get pages that have never been checked or are due for checking
        now = datetime.utcnow()
        pages = pages_collection.find({
            "is_active": True,
            "$or": [
                {"last_checked": None},
                {"last_checked": {"$lte": now}}  # This would need more complex logic for intervals
            ]
        })
        return list(pages)
    except:
        return []


def get_latest_page_version(page_id: str):
    """Get the most recent version of a page (for scheduler comparison)"""
    if db is None:
        return None
    try:
        # Get the second-to-last version for comparison (skip the most recent)
        versions = list(versions_collection.find(
            {"page_id": ObjectId(page_id)},
            sort=[("timestamp", DESCENDING)],
            limit=2
        ))
        
        # Return the previous version if we have at least 2 versions
        if len(versions) > 1:
            return versions[1]  # Second most recent
        elif len(versions) == 1:
            return None  # Only one version exists, no comparison possible
        else:
            return None  # No versions exist
    except:
        return None


# ---------------- MonitoringScheduler Class ----------------
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Optional
import logging
from .crawler import ContentFetcher

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """Background scheduler for monitoring webpage changes"""
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize the scheduler
        
        Args:
            check_interval: How often to check for pages needing monitoring (seconds)
        """
        self.check_interval = check_interval
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self._loop = None
        self.content_fetcher = ContentFetcher()  # Initialize the content fetcher
        
    async def start(self):
        """Start the monitoring scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        self._loop = asyncio.get_event_loop()
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Monitoring scheduler started")
        
    async def stop(self):
        """Stop the monitoring scheduler"""
        if not self.running:
            return
            
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring scheduler stopped")
        
    async def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self._check_pages()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _check_pages(self):
        """Check all pages that are due for monitoring"""
        try:
            # Get pages due for checking
            pages = self._get_pages_due_for_check()
            
            if not pages:
                return
                
            logger.info(f"Checking {len(pages)} pages for changes")
            
            # Process pages concurrently (but limit concurrency)
            semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
            tasks = [self._check_single_page(page, semaphore) for page in pages]
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error checking pages: {e}")
    
    def _get_pages_due_for_check(self):
        """Get pages that are actually due for checking based on their interval"""
        try:
            all_active_pages = get_pages_due_for_check()
            now = datetime.utcnow()
            due_pages = []
            
            for page in all_active_pages:
                last_checked = page.get("last_checked")
                interval_minutes = page.get("check_interval_minutes", 1440)  # Default 24 hours
                
                # If never checked, or interval has passed
                if not last_checked:
                    due_pages.append(page)
                else:
                    next_check = last_checked + timedelta(minutes=interval_minutes)
                    if now >= next_check:
                        due_pages.append(page)
            
            return due_pages
        except Exception as e:
            logger.error(f"Error getting pages due for check: {e}")
            return []
            
    async def _check_single_page(self, page, semaphore):
        """Check a single page for changes"""
        async with semaphore:
            try:
                page_id = str(page["_id"])
                url = page["url"]
                
                # Get current page content
                current_content = await self._fetch_page_content(url)
                if not current_content:
                    logger.warning(f"Failed to fetch content for {url}")
                    return
                    
                # Get the latest version for comparison
                latest_version = get_latest_page_version(page_id)
                
                # Update last_checked timestamp
                update_tracked_page(page_id, {"last_checked": datetime.utcnow()})
                
                # Check if content has changed
                if latest_version and latest_version.get("text_content") == current_content:
                    # No change detected
                    return
                    
                # Create new version
                new_version = create_page_version(page_id, current_content, url)
                if not new_version:
                    logger.error(f"Failed to create version for page {page_id}")
                    return
                    
                # Update page with new version ID
                update_data = {
                    "current_version_id": str(new_version["_id"]),
                    "last_change_detected": datetime.utcnow()
                }
                update_tracked_page(page_id, update_data)
                
                # Create change log
                change_data = {
                    "user_id": page["user_id"],
                    "page_id": page_id,
                    "change_type": "content_changed",
                    "timestamp": datetime.utcnow(),
                    "details": {
                        "url": url,
                        "content_length": len(current_content),
                        "previous_length": len(latest_version.get("text_content", "")) if latest_version else 0
                    }
                }
                
                change_log_id = create_change_log(change_data)
                if change_log_id:
                    logger.info(f"Change detected for page {page_id}: {url}")
                else:
                    logger.error(f"Failed to create change log for page {page_id}")
                    
            except Exception as e:
                logger.error(f"Error checking page {page.get('url', 'unknown')}: {e}")
                
    async def _fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch page content asynchronously using ContentFetcher"""
        try:
            # Run the synchronous crawler in a thread pool
            loop = asyncio.get_event_loop()
            html, content = await loop.run_in_executor(
                None, 
                self.content_fetcher.fetch_and_extract, 
                url
            )
            return content  # Return the extracted text content
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return None
            
    async def shutdown(self):
        """Alias for stop() method to match main.py expectations"""
        await self.stop()
        
    def schedule_page(self, page_doc):
        """
        Schedule a page for monitoring (called when new page is created)
        This is mainly for compatibility with main.py - the scheduler will pick up
        new pages automatically on its next check cycle
        """
        logger.info(f"Page scheduled for monitoring: {page_doc.get('url', 'unknown')}")
        # No immediate action needed - scheduler will pick it up automatically
        
    @property 
    def is_running(self) -> bool:
        """Property accessor to match main.py expectations"""
        return self.running