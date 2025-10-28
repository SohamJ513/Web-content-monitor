from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import List, Optional
from jose import JWTError, jwt  # ✅ Fixed import
from passlib.context import CryptContext
from pydantic import BaseModel
from bson import ObjectId   # ✅ For ObjectId validation
import asyncio
import logging

# ✅ Import database + scheduler
from .database import (
    get_user_by_email, create_user, verify_password,
    get_tracked_pages, get_tracked_page, create_tracked_page, update_tracked_page,
    get_page_versions, create_change_log, get_change_logs_for_user, create_page_version
)
from .scheduler import MonitoringScheduler

# ✅ Import your crawler
from .crawler import ContentFetcher

# ✅ Import fact check router
from .routers import fact_check

# Configure logging
logging.basicConfig(level=logging.INFO)

# JWT Settings
SECRET_KEY = "your-secret-key-change-in-production"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create FastAPI app
app = FastAPI(
    title="FreshLense API",
    description="API for web content monitoring platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
monitoring_scheduler = MonitoringScheduler()

# ✅ Initialize Crawler
crawler = ContentFetcher()

# -------------------- Pydantic Models --------------------
class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TrackedPageCreate(BaseModel):
    url: str
    display_name: Optional[str] = None
    check_interval_minutes: int = 1440

class TrackedPageResponse(BaseModel):
    id: str
    user_id: str
    url: str
    display_name: Optional[str]
    check_interval_minutes: int
    is_active: bool
    created_at: datetime
    last_checked: Optional[datetime] = None
    last_change_detected: Optional[datetime] = None
    current_version_id: Optional[str] = None

class PageVersionResponse(BaseModel):
    id: str
    page_id: str
    timestamp: datetime
    text_content: str
    metadata: dict

class ChangeLogResponse(BaseModel):
    id: str
    page_id: str
    user_id: str
    type: str
    timestamp: datetime
    description: Optional[str] = None
    semantic_similarity_score: Optional[float] = None

# -------------------- Utility functions --------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:  # ✅ Fixed exception
        raise credentials_exception

    user = get_user_by_email(email)
    if not user:
        raise credentials_exception
    return user

def normalize_doc(doc: dict) -> dict:
    """Convert MongoDB _id -> id (string) for API responses"""
    if not doc:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    if "user_id" in doc:
        doc["user_id"] = str(doc["user_id"])
    if "page_id" in doc:
        doc["page_id"] = str(doc["page_id"])
    if "current_version_id" in doc and doc["current_version_id"]:
        doc["current_version_id"] = str(doc["current_version_id"])
    return doc

# -------------------- Startup/Shutdown --------------------
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting FreshLense API...")
    await monitoring_scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down FreshLense API...")
    await monitoring_scheduler.shutdown()

# -------------------- Auth Routes --------------------
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user: UserCreate):
    existing_user = get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    new_user = create_user({"email": user.email, "password": user.password})
    return normalize_doc(new_user)

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user["email"]},
                                       expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

# -------------------- Tracked Pages Routes --------------------
@app.get("/api/pages", response_model=List[TrackedPageResponse])
async def get_my_pages(current_user: dict = Depends(get_current_user)):
    pages = get_tracked_pages(current_user["_id"])
    return [normalize_doc(p) for p in pages]

@app.post("/api/pages", response_model=TrackedPageResponse)
async def create_page(page: TrackedPageCreate, current_user: dict = Depends(get_current_user)):
    page_data = {"url": page.url, "display_name": page.display_name, "check_interval_minutes": page.check_interval_minutes}
    new_page = create_tracked_page(page_data, current_user["_id"])
    monitoring_scheduler.schedule_page(new_page)
    return normalize_doc(new_page)

@app.get("/api/pages/{page_id}", response_model=TrackedPageResponse)
async def get_page(page_id: str, current_user: dict = Depends(get_current_user)):
    try:
        ObjectId(page_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid page ID")
    page = get_tracked_page(page_id)
    if not page or page["user_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Page not found")
    return normalize_doc(page)

@app.get("/api/pages/{page_id}/versions", response_model=List[PageVersionResponse])
async def get_versions(page_id: str, current_user: dict = Depends(get_current_user)):
    try:
        ObjectId(page_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid page ID")
    page = get_tracked_page(page_id)
    if not page or page["user_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Page not found")
    versions = get_page_versions(page_id)
    return [normalize_doc(v) for v in versions]

# -------------------- Change Logs Routes --------------------
@app.get("/api/changes", response_model=List[ChangeLogResponse])
async def get_my_changes(current_user: dict = Depends(get_current_user)):
    changes = get_change_logs_for_user(current_user["_id"])
    return [normalize_doc(c) for c in changes]

# -------------------- Fact Check Routes --------------------
# ✅ Include fact check router with authentication
app.include_router(fact_check.router, dependencies=[Depends(get_current_user)])

# -------------------- Crawl Routes --------------------
@app.post("/api/crawl")
async def crawl_url(
    url: str = Query(..., description="URL to crawl"),
    current_user: dict = Depends(get_current_user)
):
    """Trigger a manual crawl for a given URL (no DB save)"""
    try:
        html_content, text_content = crawler.fetch_and_extract(url)  # ✅ Consistent variable names
        if not html_content:
            raise HTTPException(status_code=400, detail="Failed to fetch content from URL")

        return {
            "status": "success",
            "url": url,
            "html_content_length": len(html_content) if html_content else 0,  # ✅ Added HTML info
            "text_content_length": len(text_content) if text_content else 0,
            "text_content_preview": text_content[:300] if text_content else None,  # ✅ Renamed
            "full_text_content": text_content  # ✅ Renamed for clarity
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crawl/{page_id}")
async def crawl_page_by_id(page_id: str, current_user: dict = Depends(get_current_user)):
    """Trigger a manual crawl for a tracked page by its ID and store results"""
    try:
        ObjectId(page_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid page ID")

    page = get_tracked_page(page_id)
    if not page or page["user_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Page not found")

    try:
        html_content, text_content = crawler.fetch_and_extract(page["url"])
        if not html_content:
            raise HTTPException(status_code=400, detail="Failed to fetch content from URL")

        # ✅ Save new version with BOTH HTML and text content
        new_version = create_page_version(
            page_id=page_id,
            html_content=html_content,  # ✅ Now passing HTML content
            text_content=text_content,  # ✅ Keep text content
            url=page["url"]
        )
        
        if not new_version:
            raise HTTPException(status_code=500, detail="Failed to save page version")

        update_data = {
            "last_checked": datetime.utcnow(),
            "current_version_id": str(new_version["_id"])
        }

        # ✅ Compare with last version
        versions = get_page_versions(page_id)
        if len(versions) > 1 and versions[-2]["text_content"] != text_content:
            update_data["last_change_detected"] = datetime.utcnow()
            create_change_log({
                "page_id": ObjectId(page_id),
                "user_id": page["user_id"],
                "type": "manual_crawl",
                "timestamp": datetime.utcnow(),
                "description": "Content changed on manual crawl"
            })

        update_tracked_page(page_id, update_data)

        return {
            "status": "success",
            "page_id": page_id,
            "url": page["url"],
            "version_id": str(new_version["_id"]),
            "change_detected": "last_change_detected" in update_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------- Health Check --------------------
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow(), "scheduler_running": monitoring_scheduler.is_running}

@app.get("/")
async def root():
    return {"message": "FreshLense API is running!"}