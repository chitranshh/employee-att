import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    mongo_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name: str = os.getenv("MONGODB_DATABASE", "employee_attendance")
    app_name: str = os.getenv("APP_NAME", "Employee Attendance & Analytics API")

settings = Settings()
