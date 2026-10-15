from datetime import date, datetime, timezone
from bson import ObjectId

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return utc_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def serialize_document(doc: dict) -> dict:
    result = dict(doc)
    if "_id" in result:
        result["_id"] = str(result["_id"])
    for key, value in list(result.items()):
        if isinstance(value, ObjectId):
            result[key] = str(value)
    return result

def work_date_for(value: datetime) -> str:
    return value.astimezone(timezone.utc).date().isoformat()

def parse_date(value: str) -> date:
    return date.fromisoformat(value)
