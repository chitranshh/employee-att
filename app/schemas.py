from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

class PunchRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=100)
    occurred_at: datetime | None = None

    @field_validator("employee_id")
    @classmethod
    def trim_employee_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("employee_id must not be blank")
        return value

class CorrectionRequest(BaseModel):
    punch_in: datetime | None = None
    punch_out: datetime | None = None
    reason: str = Field(min_length=5, max_length=1000)
    corrected_by: str = Field(min_length=1, max_length=100)

    @field_validator("reason", "corrected_by")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

class AttendanceResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: str = Field(alias="_id")
    employee_id: str
    work_date: str
    punch_in: datetime
    punch_out: datetime | None = None
    status: Literal["open", "completed"] = "open"

class MessageResponse(BaseModel):
    message: str
