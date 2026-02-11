import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the backend folder
load_dotenv(Path(__file__).resolve().parent / ".env")

ORS_API_KEY = os.getenv("ORS_API_KEY", "").strip()
ORS_BASE_URL = os.getenv("ORS_BASE_URL", "https://api.openrouteservice.org")

APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))