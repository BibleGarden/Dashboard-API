import os


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _require(name: str) -> str:
    value = os.getenv(name, "")
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = _get_int("DB_PORT", 3306)
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "cep_admin")

# Path to MP3 files storage (inside container)
MP3_FILES_PATH = os.getenv("MP3_FILES_PATH", "audio")

# Base URL for audio files
AUDIO_BASE_URL = os.getenv("AUDIO_BASE_URL", "http://localhost:8000")

# API Authorization settings (required)
API_KEY = _require("API_KEY")

# JWT settings (required secret)
JWT_SECRET_KEY = _require("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = _get_int("JWT_EXPIRE_HOURS", 24)

# Public API database name (for cross-DB stats queries)
PUBLIC_DB_NAME = os.getenv("PUBLIC_DB_NAME", "cep_public")

# Administrator credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
