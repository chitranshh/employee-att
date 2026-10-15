# Decisions

- Use FastAPI and Pydantic for request validation and generated OpenAPI documentation.
- Use PyMongo directly so attendance listings, indexes, and analytics remain explicit.
- Store `work_date` as a UTC `YYYY-MM-DD` string to enforce one record per employee per day.
- Enforce uniqueness with a compound MongoDB index on `employee_id` and `work_date`.
- Keep corrections auditable by recording the before and after values, actor, reason, and timestamp.
- Calculate daily and employee summaries with MongoDB aggregation pipelines instead of loading all records into application memory.
- Treat timezone-less API timestamps as UTC to avoid machine-local behavior.
