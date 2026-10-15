from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta, timezone
from typing import Any

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException, Query, status
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.config import settings
from app.database import ensure_indexes, get_db
from app.schemas import CorrectionRequest, MessageResponse, PunchRequest
from app.utils import normalize_datetime, serialize_document, utc_now, work_date_for

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        ensure_indexes()
    except Exception:
        
        pass
    yield

app = FastAPI(
    title=settings.app_name,
    description="Punch-in/out, audited attendance corrections, and MongoDB aggregation analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

def database_or_503(db: Database) -> Database:
    try:
        db.command("ping")
        return db
    except Exception as exc:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable. Check MONGODB_URI.") from exc

def get_document_or_404(db: Database, attendance_id: str) -> dict:
    if not ObjectId.is_valid(attendance_id):
        raise HTTPException(status_code=400, detail="Invalid attendance_id")
    doc = db.attendance.find_one({"_id": ObjectId(attendance_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return doc

@app.get("/health")
def health(db: Database = Depends(get_db)) -> dict:
    database_or_503(db)
    return {"status": "ok", "database": "connected"}

@app.post("/attendance/punch-in", status_code=status.HTTP_201_CREATED)
def punch_in(payload: PunchRequest, db: Database = Depends(get_db)) -> dict:
    database_or_503(db)
    occurred_at = normalize_datetime(payload.occurred_at)
    if occurred_at > utc_now() + timedelta(minutes=2):
        raise HTTPException(status_code=422, detail="Punch-in time cannot be in the future")
    work_date = work_date_for(occurred_at)
    existing = db.attendance.find_one({"employee_id": payload.employee_id, "work_date": work_date})
    if existing:
        if existing.get("punch_out") is None:
            raise HTTPException(status_code=409, detail="Employee already has an open attendance record")
        raise HTTPException(status_code=409, detail="Attendance already exists for this employee and date")
    doc = {
        "employee_id": payload.employee_id,
        "work_date": work_date,
        "punch_in": occurred_at,
        "punch_out": None,
        "status": "open",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    try:
        result = db.attendance.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Attendance already exists for this employee and date") from exc
    doc["_id"] = result.inserted_id
    return serialize_document(doc)

@app.post("/attendance/punch-out")
def punch_out(payload: PunchRequest, db: Database = Depends(get_db)) -> dict:
    database_or_503(db)
    occurred_at = normalize_datetime(payload.occurred_at)
    if occurred_at > utc_now() + timedelta(minutes=2):
        raise HTTPException(status_code=422, detail="Punch-out time cannot be in the future")
    work_date = work_date_for(occurred_at)
    record = db.attendance.find_one({"employee_id": payload.employee_id, "work_date": work_date})
    if not record:
        raise HTTPException(status_code=404, detail="No attendance record found for this employee and date")
    if record.get("punch_out") is not None:
        raise HTTPException(status_code=409, detail="Employee has already punched out")
    if occurred_at <= record["punch_in"]:
        raise HTTPException(status_code=422, detail="Punch-out must be after punch-in")
    db.attendance.update_one(
        {"_id": record["_id"], "punch_out": None},
        {"$set": {"punch_out": occurred_at, "status": "completed", "updated_at": utc_now()}},
    )
    updated = db.attendance.find_one({"_id": record["_id"]})
    return serialize_document(updated)

@app.get("/attendance")
def list_attendance(
    employee_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db: Database = Depends(get_db),
) -> dict:
    database_or_503(db)
    query: dict[str, Any] = {}
    if employee_id:
        query["employee_id"] = employee_id.strip()
    if start_date or end_date:
        date_filter: dict[str, str] = {}
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="start_date must use YYYY-MM-DD") from exc
            date_filter["$gte"] = start_date
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="end_date must use YYYY-MM-DD") from exc
            date_filter["$lte"] = end_date
        query["work_date"] = date_filter
    cursor = db.attendance.find(query).sort([("work_date", DESCENDING), ("employee_id", ASCENDING)]).skip(skip).limit(limit)
    items = [serialize_document(doc) for doc in cursor]
    return {"items": items, "limit": limit, "skip": skip, "count": len(items)}

@app.patch("/attendance/{attendance_id}/correction")
def correct_attendance(attendance_id: str, payload: CorrectionRequest, db: Database = Depends(get_db)) -> dict:
    database_or_503(db)
    old = get_document_or_404(db, attendance_id)
    new_punch_in = normalize_datetime(payload.punch_in) if payload.punch_in is not None else old["punch_in"]
    if payload.punch_out is not None:
        new_punch_out = normalize_datetime(payload.punch_out)
    else:
        new_punch_out = old.get("punch_out")
    if new_punch_in > utc_now() + timedelta(minutes=2):
        raise HTTPException(status_code=422, detail="Punch-in time cannot be in the future")
    if new_punch_out is not None:
        if new_punch_out > utc_now() + timedelta(minutes=2):
            raise HTTPException(status_code=422, detail="Punch-out time cannot be in the future")
        if new_punch_out <= new_punch_in:
            raise HTTPException(status_code=422, detail="Punch-out must be after punch-in")
    changed_at = utc_now()
    new_values = {
        "punch_in": new_punch_in,
        "punch_out": new_punch_out,
        "status": "completed" if new_punch_out is not None else "open",
        "updated_at": changed_at,
    }
   
    audit = {
        "attendance_id": str(old["_id"]),
        "employee_id": old["employee_id"],
        "changed_by": payload.corrected_by,
        "reason": payload.reason,
        "changed_at": changed_at,
        "before": {"punch_in": old["punch_in"], "punch_out": old.get("punch_out"), "status": old.get("status")},
        "after": {"punch_in": new_punch_in, "punch_out": new_punch_out, "status": new_values["status"]},
    }
    db.audit_logs.insert_one(audit)
    db.attendance.update_one({"_id": old["_id"]}, {"$set": new_values})
    updated = db.attendance.find_one({"_id": old["_id"]})
    return {"attendance": serialize_document(updated), "audit": serialize_document(audit)}

@app.get("/attendance/{attendance_id}/audit")
def attendance_audit(attendance_id: str, db: Database = Depends(get_db)) -> dict:
    database_or_503(db)
    record = get_document_or_404(db, attendance_id)
    logs = db.audit_logs.find({"attendance_id": str(record["_id"])}).sort("changed_at", DESCENDING)
    return {"items": [serialize_document(item) for item in logs]}

@app.get("/analytics/daily")
def daily_analytics(
    start_date: str = Query(..., description="Inclusive date in YYYY-MM-DD"),
    end_date: str = Query(..., description="Inclusive date in YYYY-MM-DD"),
    db: Database = Depends(get_db),
) -> dict:
    database_or_503(db)
    for name, value in (("start_date", start_date), ("end_date", end_date)):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{name} must use YYYY-MM-DD") from exc
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")
    pipeline = [
        {"$match": {"work_date": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {
            "_id": "$work_date",
            "total_records": {"$sum": 1},
            "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            "open_records": {"$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}},
            "employees": {"$addToSet": "$employee_id"},
            "total_worked_minutes": {"$sum": {
                "$cond": [
                    {"$and": [{"$ne": ["$punch_out", None]}, {"$ne": [{"$type": "$punch_out"}, "missing"]}]},
                    {"$divide": [{"$subtract": ["$punch_out", "$punch_in"]}, 60000]},
                    0
                ]
            }},
        }},
        {"$project": {
            "_id": 0, "date": "$_id", "total_records": 1, "completed": 1, "open_records": 1,
            "employee_count": {"$size": "$employees"},
            "total_worked_minutes": {"$round": ["$total_worked_minutes", 2]},
        }},
        {"$sort": {"date": 1}},
    ]
    return {"items": list(db.attendance.aggregate(pipeline)), "start_date": start_date, "end_date": end_date}

@app.get("/analytics/employee/{employee_id}")
def employee_analytics(
    employee_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Database = Depends(get_db),
) -> dict:
    database_or_503(db)
    match: dict[str, Any] = {"employee_id": employee_id}
    if start_date or end_date:
        bounds: dict[str, str] = {}
        for name, value in (("start_date", start_date), ("end_date", end_date)):
            if value:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=f"{name} must use YYYY-MM-DD") from exc
                bounds["$gte" if name == "start_date" else "$lte"] = value
        match["work_date"] = bounds
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$employee_id",
            "days_recorded": {"$sum": 1},
            "completed_days": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            "open_days": {"$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}},
            "total_worked_minutes": {"$sum": {
                "$cond": [
                    {"$and": [{"$ne": ["$punch_out", None]}, {"$ne": [{"$type": "$punch_out"}, "missing"]}]},
                    {"$divide": [{"$subtract": ["$punch_out", "$punch_in"]}, 60000]},
                    0
                ]
            }},
            "first_punch_in": {"$min": "$punch_in"},
            "last_punch_in": {"$max": "$punch_in"},
        }},
        {"$project": {
            "_id": 0, "employee_id": "$_id", "days_recorded": 1, "completed_days": 1, "open_days": 1,
            "total_worked_minutes": {"$round": ["$total_worked_minutes", 2]},
            "average_worked_minutes": {"$cond": [
                {"$gt": ["$completed_days", 0]},
                {"$round": [{"$divide": ["$total_worked_minutes", "$completed_days"]}, 2]},
                0
            ]},
            "first_punch_in": 1, "last_punch_in": 1,
        }},
    ]
    result = list(db.attendance.aggregate(pipeline))
    if not result:
        return {"employee_id": employee_id, "days_recorded": 0, "completed_days": 0, "open_days": 0,
                "total_worked_minutes": 0, "average_worked_minutes": 0, "first_punch_in": None, "last_punch_in": None}
    return result[0]

@app.get("/audit")
def list_audit_logs(
    employee_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Database = Depends(get_db),
) -> dict:
    database_or_503(db)
    query = {"employee_id": employee_id} if employee_id else {}
    items = [serialize_document(doc) for doc in db.audit_logs.find(query).sort("changed_at", DESCENDING).limit(limit)]
    return {"items": items, "count": len(items)}

@app.get("/")
def root() -> dict:
    return {"message": "Employee Attendance & Analytics API", "docs": "/docs", "health": "/health"}
