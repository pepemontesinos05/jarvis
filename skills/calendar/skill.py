# skills/calendar/skill.py

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config.settings import TIMEZONE
from services.llm import extract_calendar_intent
from services.date_resolver import resolve_date, resolve_structured_time
from services.google_calendar import list_events, create_event, update_event, delete_event
from skills.base import Skill, SkillResult

DEFAULT_EVENT_DURATION_HOURS = 1
SEARCH_WINDOW_DAYS = 30  # rango donde buscar un evento existente por título


def _is_valid_extraction(result: dict | None) -> bool:
    if result is None:
        return False

    action = result.get("action")
    if action not in ("crear", "actualizar", "eliminar"):
        return False

    if action in ("crear", "actualizar") and not result.get("date_expression") and not result.get("time"):
        return False

    if action == "crear" and not result.get("title"):
        return False

    return True


def _combine_date_and_time(base_date: datetime, time_obj: dict | None, tz: ZoneInfo) -> datetime | None:
    """Combina la fecha resuelta con la hora resuelta en un único datetime con zona horaria.

    Si no hay time_obj, se asume la hora actual del 'base_date' (útil si el
    usuario solo dio fecha, sin hora concreta).
    """
    if time_obj is None:
        return base_date.replace(tzinfo=tz)

    resolved_time = resolve_structured_time(time_obj)
    if resolved_time is None:
        return None

    return datetime.combine(base_date.date(), resolved_time, tzinfo=tz)


def _find_event_by_title(title: str, now: datetime) -> list[dict]:
    """Busca eventos cuyo título contenga 'title' (case-insensitive) en una
    ventana de búsqueda razonable alrededor de 'now'.
    """
    window_start = now - timedelta(days=1)
    window_end = now + timedelta(days=SEARCH_WINDOW_DAYS)

    events = list_events(time_min=window_start, time_max=window_end, max_results=50)

    title_lower = title.lower()
    return [e for e in events if title_lower in e.get("summary", "").lower()]


class CalendarSkill(Skill):
    @property
    def intent_name(self) -> str:
        return "calendar"

    @property
    def keywords(self) -> list[str]:
        return ["calendario", "cita", "evento", "reunión", "agenda", "recordatorio"]

    def execute(self, parameters: dict) -> SkillResult:
        order = parameters.get("raw_text", "")
        if not order:
            return SkillResult(success=False, message="No he recibido ninguna orden para procesar.")

        extraction = extract_calendar_intent(order)

        if not _is_valid_extraction(extraction):
            # TODO: aquí entrará el fallback a Gemini (pendiente de implementar)
            return SkillResult(success=False, message="No he entendido bien la orden, ¿puedes repetirla de otra forma?")

        tz = ZoneInfo(TIMEZONE)
        now = datetime.now(tz)
        action = extraction["action"]

        if action == "crear":
            return self._handle_create(extraction, now, tz)
        if action == "actualizar":
            return self._handle_update(extraction, now, tz)
        if action == "eliminar":
            return self._handle_delete(extraction, now, tz)

        return SkillResult(success=False, message="No he sabido qué hacer con esa orden.")

    def _handle_create(self, extraction: dict, now: datetime, tz: ZoneInfo) -> SkillResult:
        base_date = resolve_date(extraction.get("date_expression"), now) or now
        start = _combine_date_and_time(base_date, extraction.get("time"), tz)

        if start is None:
            return SkillResult(success=False, message="No he entendido bien la hora que me has dicho.")

        end = start + timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)

        try:
            event = create_event(summary=extraction["title"], start=start, end=end)
        except Exception:
            return SkillResult(success=False, message="Ha habido un problema al crear el evento en tu calendario.")

        fecha_legible = start.strftime("%d/%m a las %H:%M")
        return SkillResult(
            success=True,
            message=f"Hecho, he creado '{extraction['title']}' el {fecha_legible}.",
            data={"event_id": event["id"]},
        )

    def _handle_delete(self, extraction: dict, now: datetime, tz: ZoneInfo) -> SkillResult:
        title = extraction.get("title")
        if not title:
            return SkillResult(success=False, message="No sé qué evento quieres cancelar, dime el título.")

        matches = _find_event_by_title(title, now)

        if not matches:
            return SkillResult(success=False, message=f"No he encontrado ningún evento llamado '{title}'.")

        if len(matches) > 1:
            return SkillResult(success=False, message=f"He encontrado varios eventos parecidos a '{title}', sé más específico.")

        event = matches[0]

        try:
            delete_event(event["id"])
        except Exception:
            return SkillResult(success=False, message="Ha habido un problema al cancelar el evento.")

        return SkillResult(success=True, message=f"Hecho, he cancelado '{title}'.")

    def _handle_update(self, extraction: dict, now: datetime, tz: ZoneInfo) -> SkillResult:
        title = extraction.get("title")
        if not title:
            return SkillResult(success=False, message="No sé qué evento quieres mover, dime el título.")

        matches = _find_event_by_title(title, now)

        if not matches:
            return SkillResult(success=False, message=f"No he encontrado ningún evento llamado '{title}'.")

        if len(matches) > 1:
            return SkillResult(success=False, message=f"He encontrado varios eventos parecidos a '{title}', sé más específico.")

        event = matches[0]

        base_date = resolve_date(extraction.get("date_expression"), now) or now
        new_start = _combine_date_and_time(base_date, extraction.get("time"), tz)

        if new_start is None:
            return SkillResult(success=False, message="No he entendido bien la nueva hora que me has dicho.")

        new_end = new_start + timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)

        try:
            update_event(event["id"], start=new_start, end=new_end)
        except Exception:
            return SkillResult(success=False, message="Ha habido un problema al mover el evento.")

        fecha_legible = new_start.strftime("%d/%m a las %H:%M")
        return SkillResult(success=True, message=f"Hecho, he movido '{title}' al {fecha_legible}.")