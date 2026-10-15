# Employee Attendance API

FastAPI service for employee punch-in/out records, audited corrections, and MongoDB-backed attendance analytics.

## Setup

Requires Python 3.11+ and MongoDB. MongoDB Atlas or a local MongoDB instance can be used.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Set `MONGODB_URI` and `MONGODB_DATABASE` in `.env`. Never commit `.env`.

Swagger UI is available at `http://127.0.0.1:8000/docs`.

## Endpoints

- `POST /attendance/punch-in` and `POST /attendance/punch-out`
- `GET /attendance` with employee, date, and pagination filters
- `PATCH /attendance/{attendance_id}/correction`
- `GET /attendance/{attendance_id}/audit` and `GET /audit`
- `GET /analytics/daily`
- `GET /analytics/employee/{employee_id}`
- `GET /health`

Attendance is limited to one record per employee per UTC calendar day. Corrections require a reason and actor, and analytics use MongoDB aggregation pipelines.

Run tests with:

```bash
python -m pytest -q
```
