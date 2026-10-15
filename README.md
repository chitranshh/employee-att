# Employee Attendance API

This is a small FastAPI service for recording employee attendance. It keeps punch-in and punch-out records in MongoDB, allows authorised staff to correct mistakes, and provides a couple of useful attendance summaries.

## Setup

The application needs Python 3.11 or newer and a MongoDB database. A local MongoDB instance and MongoDB Atlas both work.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Before starting the server, set these environment variables in a local `.env` file or in your shell:

```text
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=employee_attendance
```

The `.env` file is intentionally kept out of Git.

Once the server is running, the interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Endpoints

- `POST /attendance/punch-in` and `POST /attendance/punch-out` record working time.
- `GET /attendance` lists records with employee, date, and pagination filters.
- `PATCH /attendance/{attendance_id}/correction` changes a record and creates an audit entry.
- `GET /attendance/{attendance_id}/audit` and `GET /audit` expose correction history.
- `GET /analytics/daily` and `GET /analytics/employee/{employee_id}` return summaries.
- `GET /health` checks that the API can reach MongoDB.

There can be one attendance record per employee for each UTC calendar day. Punch times are normalised to UTC, and corrections require both a reason and the person making the correction. The analytics are calculated with MongoDB aggregation pipelines rather than by loading every record into Python.

Run the tests with:

```bash
python -m pytest -q
```
