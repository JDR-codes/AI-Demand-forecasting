import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
     "DATABASE_URL",
     "mysql+pymysql://root:password@localhost:3306/ai_demand_forecast"
)
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

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

# Base directory for fastapi_app
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Path configurations for uploads, models, and data
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
MODELS_DIR = os.path.join(BASE_DIR, "model_artifacts")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure directories exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_DATASET_PATH = os.getenv(
    "DEFAULT_DATASET_PATH",
    os.path.join(DATA_DIR, "demand forecasting dataset.csv")
)

REGISTRY_PATH = os.path.join(MODELS_DIR, "registry.json")

ACCESS_TOKEN_EXPIRE = timedelta(
    minutes=ACCESS_TOKEN_EXPIRE_MINUTES
)

# ── SMTP / Email (forgot-password OTP) ──────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)