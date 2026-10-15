# Decisions

## Why FastAPI and Pydantic

FastAPI gives the service a simple route structure and useful API documentation. Pydantic handles the input rules, such as trimming employee IDs and requiring a reason for a correction, before the database is touched.

## Why direct PyMongo

The database operations are deliberately visible in the endpoint code. This makes the unique indexes, filters, and aggregation pipelines easy to inspect and keeps the MongoDB-specific behavior under control.

## Attendance dates and uniqueness

`work_date` is stored as a UTC `YYYY-MM-DD` string. The compound unique index on `employee_id` and `work_date` enforces the one-record-per-employee-per-day rule even when two requests arrive at nearly the same time.

## Corrections and audit history

Every correction records the previous values, the new values, the reason, the actor, and the timestamp. The audit entry is written before the attendance update so an attempted change is not silently lost if the second write fails.

## Analytics

Daily and employee summaries use MongoDB aggregation pipelines. The database performs the grouping and time calculations, so the API does not need to load the entire attendance collection into memory.

## Time handling

Timezone-less timestamps are treated as UTC. That avoids depending on the machine's local timezone and keeps comparisons consistent across development and deployment environments.
