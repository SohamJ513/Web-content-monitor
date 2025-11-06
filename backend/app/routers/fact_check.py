from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from ..database import (
    versions_collection, 
    pages_collection, 
    get_page_versions,
    get_tracked_page,
    doc_to_dict
)
from ..services.fact_check_service import FactCheckService
from ..services.diff_service import DiffService
from ..schemas.fact_check import FactCheckRequest, FactCheckResponse, FactCheckItem, ClaimType, Verdict
from ..schemas.diff import DiffRequest, DiffResponse, ContentChange

router = APIRouter(prefix="/api/fact-check", tags=["fact-check"])

# 🚨 CRITICAL FIX: Create service instance inside functions to avoid caching issues
# Don't create at module level - create fresh instances when needed

diff_service = DiffService()

@router.post("/check", response_model=FactCheckResponse)
async def fact_check_page(request: FactCheckRequest, current_user: dict = Depends(lambda: None)):
    """Perform fact checking on a page version"""
    try:
        # 🚨 CRITICAL FIX: Create fresh FactCheckService instance
        fact_check_service = FactCheckService()
        print("🔄 DEBUG: Created fresh FactCheckService instance")
        
        # Get the specific page version
        version = versions_collection.find_one({"_id": ObjectId(request.version_id)})
        if not version:
            raise HTTPException(status_code=404, detail="Page version not found")
        
        # Get page info and verify ownership
        page = get_tracked_page(str(version["page_id"]))
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")
        
        # Perform fact checking on text content
        text_content = version.get("text_content", "")
        print(f"🔍 DEBUG: Starting fact check on {len(text_content)} chars of content")
        fact_check_results = await fact_check_service.check_content(text_content)
        
        return FactCheckResponse(
            page_id=str(version["page_id"]),
            version_id=request.version_id,
            page_url=page.get("url", ""),
            page_title=page.get("display_name", ""),
            checked_at=datetime.utcnow(),
            results=fact_check_results,
            total_claims=len(fact_check_results),
            verified_claims=len([r for r in fact_check_results if r.verdict == Verdict.TRUE]),
            unverified_claims=len([r for r in fact_check_results if r.verdict == Verdict.FALSE]),
            inconclusive_claims=len([r for r in fact_check_results if r.verdict == Verdict.UNVERIFIED])
        )
        
    except Exception as e:
        print(f"💥 Fact checking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fact checking failed: {str(e)}")

@router.post("/check-direct", response_model=FactCheckResponse)
async def fact_check_direct_content(request: dict, current_user: dict = Depends(lambda: None)):
    """Perform fact checking on directly provided text content"""
    try:
        # 🚨 CRITICAL FIX: Create fresh FactCheckService instance
        fact_check_service = FactCheckService()
        print("🔄 DEBUG: Created fresh FactCheckService instance for direct check")
        
        text_content = request.get("content", "")
        page_url = request.get("page_url", "Direct input")
        page_title = request.get("page_title", "User provided content")
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Content cannot be empty")
        
        # Limit content length to prevent abuse
        if len(text_content) > 15000:
            text_content = text_content[:15000] + "... [content truncated]"
        
        print(f"🔍 DEBUG: Starting direct fact check on {len(text_content)} chars of content")
        # Perform fact checking on direct text content
        fact_check_results = await fact_check_service.check_content(text_content)
        
        return FactCheckResponse(
            page_id="direct_input",
            version_id="direct_input",
            page_url=page_url,
            page_title=page_title,
            checked_at=datetime.utcnow(),
            results=fact_check_results,
            total_claims=len(fact_check_results),
            verified_claims=len([r for r in fact_check_results if r.verdict == Verdict.TRUE]),
            unverified_claims=len([r for r in fact_check_results if r.verdict == Verdict.FALSE]),
            inconclusive_claims=len([r for r in fact_check_results if r.verdict == Verdict.UNVERIFIED])
        )
        
    except Exception as e:
        print(f"💥 Direct fact checking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Direct fact checking failed: {str(e)}")

@router.post("/compare", response_model=DiffResponse)
async def compare_versions(request: DiffRequest, current_user: dict = Depends(lambda: None)):
    """Compare two page versions and show differences"""
    try:
        # Get both versions
        old_version = versions_collection.find_one({"_id": ObjectId(request.old_version_id)})
        new_version = versions_collection.find_one({"_id": ObjectId(request.new_version_id)})
        
        if not old_version or not new_version:
            raise HTTPException(status_code=404, detail="One or both versions not found")
        
        if str(old_version["page_id"]) != str(new_version["page_id"]):
            raise HTTPException(status_code=400, detail="Versions must be from the same page")
        
        # Perform diff comparison
        old_text = old_version.get("text_content", "")
        new_text = new_version.get("text_content", "")
        
        diff_result = diff_service.compare_text(old_text, new_text)
        
        return DiffResponse(
            page_id=str(old_version["page_id"]),
            old_version_id=request.old_version_id,
            new_version_id=request.new_version_id,
            old_timestamp=old_version["timestamp"],
            new_timestamp=new_version["timestamp"],
            changes=diff_result,
            total_changes=len(diff_result)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")

@router.get("/page/{page_id}/versions")
async def get_page_versions_for_factcheck(page_id: str, limit: int = 20, current_user: dict = Depends(lambda: None)):
    """Get page versions with basic info for fact check UI"""
    try:
        versions = get_page_versions(page_id, limit)
        page = get_tracked_page(page_id)
        
        version_list = []
        for version in versions:
            version_list.append({
                "version_id": str(version["_id"]),
                "timestamp": version["timestamp"],
                "content_preview": version.get("text_content", "")[:200] + "..." if len(version.get("text_content", "")) > 200 else version.get("text_content", ""),
                "word_count": version.get("metadata", {}).get("word_count", 0),
                "content_length": version.get("metadata", {}).get("content_length", 0)
            })
        
        return {
            "page_info": {
                "page_id": page_id,
                "url": page.get("url", "") if page else "",
                "display_name": page.get("display_name", "") if page else ""
            },
            "versions": version_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get versions: {str(e)}")

@router.get("/debug-serb")
async def debug_serp_integration():
    """Debug SERP API integration"""
    try:
        # 🚨 CRITICAL FIX: Create fresh FactCheckService instance
        fact_check_service = FactCheckService()
        print("🔄 DEBUG: Created fresh FactCheckService instance for debug")
        
        # Check configuration
        config_status = fact_check_service.check_serp_status()
        
        # Test a claim that should trigger SERP API
        test_claim = {
            "text": "Python 3.6 offers 50% better performance than Python 2.7",
            "type": ClaimType.PERFORMANCE,
            "technical_indicators": {
                "technologies": ["python"],
                "versions": ["3.6", "2.7"],
                "numbers": ["50%"]
            }
        }
        
        result = await fact_check_service.verify_claim_enhanced(test_claim)
        
        return {
            "config_status": config_status,
            "test_claim": test_claim["text"],
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug endpoint failed: {str(e)}")