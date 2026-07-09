import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/ai_demand_forecast"
)

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

# ============================================================================
# PROJECT PATHS
# ============================================================================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MEDIA_DIR = os.path.join(BASE_DIR, "media")
MODELS_DIR = os.path.join(BASE_DIR, "model_artifacts")
DATA_DIR = os.path.join(BASE_DIR, "data")
# UPLOAD_DIR = os.path.join(MEDIA_DIR, "uploads")

DEFAULT_DATASET_PATH = os.getenv(
    "DEFAULT_DATASET_PATH",
    os.path.join(DATA_DIR, "demand forecasting dataset.csv")
)

REGISTRY_PATH = os.path.join(MODELS_DIR, "registry.json")

# Create only the root folders
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
# os.makedirs(UPLOAD_DIR, exist_ok=True)

ACCESS_TOKEN_EXPIRE = timedelta(
    minutes=ACCESS_TOKEN_EXPIRE_MINUTES
)

# ============================================================================
# Cookie settings (access_token / refresh_token / otp_session)
# ============================================================================
# COOKIE_SECURE=True requires HTTPS — the browser silently drops secure
# cookies sent over plain http. Set COOKIE_SECURE=False in .env for local
# http://127.0.0.1 development; keep it True (the default) in production.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")  # "lax" | "strict" | "none"
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
OTP_SESSION_EXPIRE_MINUTES = int(os.getenv("OTP_SESSION_EXPIRE_MINUTES", "5"))

# ============================================================================
# SMTP / Email
# ============================================================================

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)