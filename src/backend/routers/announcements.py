"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable format"""
    if announcement and "_id" in announcement:
        announcement["id"] = str(announcement["_id"])
        del announcement["_id"]
    return announcement


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (not expired)"""
    current_time = datetime.utcnow().isoformat()
    
    # Find announcements where expiration_date is in the future
    # and start_date is either null or in the past
    query = {
        "expiration_date": {"$gte": current_time}
    }
    
    announcements = []
    for announcement in announcements_collection.find(query):
        # Check if start_date exists and is in the future
        start_date = announcement.get("start_date")
        if start_date and start_date > current_time:
            continue  # Skip announcements that haven't started yet
        
        announcements.append(serialize_announcement(announcement))
    
    return announcements


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Get all announcements (including expired) - requires authentication"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Return all announcements, sorted by expiration date (newest first)
    announcements = []
    for announcement in announcements_collection.find().sort("expiration_date", -1):
        announcements.append(serialize_announcement(announcement))
    
    return announcements


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_announcement(
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new announcement - requires authentication"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate dates
    try:
        expiration_datetime = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid expiration_date format. Use ISO format.")
    
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid start_date format. Use ISO format.")
    
    # Create the announcement document
    announcement_doc = {
        "message": message,
        "expiration_date": expiration_date,
        "start_date": start_date,
        "created_by": teacher_username,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = announcements_collection.insert_one(announcement_doc)
    announcement_doc["id"] = str(result.inserted_id)
    del announcement_doc["_id"]
    
    return announcement_doc


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update an existing announcement - requires authentication"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate dates
    try:
        exp_dt = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid expiration_date format. Use ISO format.")
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid start_date format. Use ISO format.")
    
    # Update the announcement
    try:
        result = announcements_collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {
                "$set": {
                    "message": message,
                    "expiration_date": expiration_date,
                    "start_date": start_date,
                    "updated_by": teacher_username,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Fetch and return the updated announcement
    updated_announcement = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    return serialize_announcement(updated_announcement)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """Delete an announcement - requires authentication"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Delete the announcement
    try:
        result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
