from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.schemas import CorrectionRequest, PunchRequest
from app.utils import normalize_datetime, work_date_for

def test_employee_id_is_trimmed():
    assert PunchRequest(employee_id="  EMP001 ").employee_id == "EMP001"

def test_blank_employee_id_is_rejected():
    with pytest.raises(ValidationError):
        PunchRequest(employee_id="   ")

def test_correction_requires_reason_and_actor():
    with pytest.raises(ValidationError):
        CorrectionRequest(reason=" ", corrected_by="manager")

def test_naive_datetime_is_treated_as_utc():
    value = normalize_datetime(datetime(2026, 10, 13, 9, 0, 0))
    assert value.tzinfo == timezone.utc
    assert value.hour == 9

def test_work_date_uses_utc():
    value = datetime(2026, 10, 13, 23, 30, tzinfo=timezone.utc)
    assert work_date_for(value) == "2026-10-13"
