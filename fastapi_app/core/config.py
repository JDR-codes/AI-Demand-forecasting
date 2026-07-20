# fastapi_app/core/config.py

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# DATABASE
# ============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./demand_forecast.db"  # Changed to SQLite as default for development
)

# ============================================================================
# JWT / SECURITY
# ============================================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change_this_secret_in_production"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

ACCESS_TOKEN_EXPIRE = timedelta(
    minutes=ACCESS_TOKEN_EXPIRE_MINUTES
)

# ============================================================================
# PROJECT PATHS
# ============================================================================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # Fixed: goes up to project root

MEDIA_DIR = os.path.join(BASE_DIR, "fastapi_app", "media")  # Fixed: inside fastapi_app
MODELS_DIR = os.path.join(BASE_DIR, "model_artifacts")
DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULT_DATASET_PATH = os.getenv(
    "DEFAULT_DATASET_PATH",
    os.path.join(DATA_DIR, "demand_forecasting_dataset.csv")
)

REGISTRY_PATH = os.path.join(MODELS_DIR, "registry.json")

# Create directories
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================================================
# COOKIE SETTINGS
# ============================================================================

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # Fixed: default False for dev
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
OTP_SESSION_EXPIRE_MINUTES = int(os.getenv("OTP_SESSION_EXPIRE_MINUTES", "5"))

# ============================================================================
# SMTP / EMAIL
# ============================================================================

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)

# ============================================================================
# CORS
# ============================================================================

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")