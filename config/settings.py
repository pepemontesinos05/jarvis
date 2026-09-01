from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

TIMEZONE = os.getenv("JARVIS_TIMEZONE", "Europe/Madrid")
GOOGLE_CREDENTIALS_PATH = BASE_DIR / os.getenv("GOOGLE_CREDENTIALS_PATH", "config/secrets/google_credentials.json")
GOOGLE_TOKEN_PATH = BASE_DIR / os.getenv("GOOGLE_TOKEN_PATH", "config/secrets/google_token.json")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")