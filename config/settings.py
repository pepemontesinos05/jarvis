from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

TIMEZONE = os.getenv("JARVIS_TIMEZONE", "Europe/Madrid")
GOOGLE_CREDENTIALS_PATH = BASE_DIR / os.getenv("GOOGLE_CREDENTIALS_PATH", "config/secrets/google_credentials.json")
GOOGLE_TOKEN_PATH = BASE_DIR / os.getenv("GOOGLE_TOKEN_PATH", "config/secrets/google_token.json")