from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

BASE_DIR = Path(__file__).resolve().parent.parent
SECRETS_DIR = BASE_DIR / "config" / "secrets"
CREDENTIALS_PATH = SECRETS_DIR / "google_credentials.json"
TOKEN_PATH = SECRETS_DIR / "google_token.json"


def get_calendar_service():
    """Devuelve un cliente autenticado de Google Calendar.

    Reutiliza el token guardado si es válido, lo refresca si caducó,
    o lanza el flujo de login en el navegador si no existe todavía.
    """
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


# Prueba rápida para verificar que la autenticación funciona
if __name__ == "__main__":
    service = get_calendar_service()
    print("Conexión establecida correctamente con Google Calendar.")
    print(service)