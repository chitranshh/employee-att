from functools import lru_cache
from pymongo import MongoClient
from pymongo.database import Database
from app.config import settings

@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000, tz_aware=True)

def get_db() -> Database:
    return get_client()[settings.database_name]

def ensure_indexes() -> None:
    db = get_db()
    db.attendance.create_index([("employee_id", 1), ("work_date", 1)], unique=True)
    db.attendance.create_index([("work_date", 1), ("employee_id", 1)])
    db.attendance.create_index([("employee_id", 1), ("punch_in", -1)])
    db.audit_logs.create_index([("attendance_id", 1), ("changed_at", -1)])
    db.audit_logs.create_index([("employee_id", 1), ("changed_at", -1)])
