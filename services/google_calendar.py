# services/google_calendar.py

from pathlib import Path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

BASE_DIR = Path(__file__).resolve().parent.parent
SECRETS_DIR = BASE_DIR / "config" / "secrets"
CREDENTIALS_PATH = SECRETS_DIR / "google_credentials.json"
TOKEN_PATH = SECRETS_DIR / "google_token.json"

TIMEZONE = "Europe/Madrid"


def get_calendar_service():
    """Devuelve un cliente autenticado de Google Calendar."""
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
            creds = flow.run_local_server(port=0, open_browser=False)

        TOKEN_PATH.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _to_stand_format(dt: datetime) -> dict:
    """Convierte un datetime de Python al formato que espera la API de Google."""
    return {"dateTime": dt.isoformat(), "timeZone": TIMEZONE}


def list_events(time_min: datetime, time_max: datetime, 
                max_results: int = 10, calendar_id: str = "primary"):
    """Lista eventos entre dos fechas, ordenados cronológicamente."""
    service = get_calendar_service()
    result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return result.get("items", [])


def get_event(event_id: str, calendar_id: str = "primary"):
    """Obtiene el detalle de un evento concreto."""
    service = get_calendar_service()
    return service.events().get(calendarId=calendar_id, eventId=event_id).execute()


def create_event(summary: str, start: datetime, end: datetime, description: str = None,
                  location: str = None, calendar_id: str = "primary"):
    """Crea un evento nuevo y devuelve el evento creado (incluye su 'id')."""
    service = get_calendar_service()
    body = {
        "summary": summary,
        "start": _to_stand_format(start),
        "end": _to_stand_format(end),
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    return service.events().insert(calendarId=calendar_id, body=body).execute()


def update_event(event_id: str, calendar_id: str = "primary", **fields):
    """Edita parcialmente un evento existente.

    Ejemplo: update_event(event_id, start=nuevo_inicio, end=nuevo_fin)
    """
    service = get_calendar_service()
    body = {}
    if "start" in fields:
        body["start"] = _to_stand_format(fields["start"])
    if "end" in fields:
        body["end"] = _to_stand_format(fields["end"])
    if "summary" in fields:
        body["summary"] = fields["summary"]
    if "description" in fields:
        body["description"] = fields["description"]
    if "location" in fields:
        body["location"] = fields["location"]

    return service.events().patch(calendarId=calendar_id, eventId=event_id, body=body).execute()


def delete_event(event_id: str, calendar_id: str = "primary"):
    """Elimina un evento. No devuelve contenido si tiene éxito."""
    service = get_calendar_service()
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()