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
    if action not in ("crear", "actualizar", "eliminar", "listar"):
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

STOPWORDS = {"el", "la", "los", "las", "de", "del", "un", "una", "con", "y", "a", "en"}

def _extract_keywords(text: str) -> set[str]:
    """Convierte un título en un conjunto de palabras significativas (sin stopwords)."""
    words = text.lower().split()
    return {w for w in words if w not in STOPWORDS and len(w) > 2}

def _find_event_by_title(title: str, now: datetime) -> list[dict]:
    """Busca eventos por substring exacto, o por coincidencia de palabras clave
    significativas si el substring no encuentra nada."""
    window_start = now - timedelta(days=1)
    window_end = now + timedelta(days=SEARCH_WINDOW_DAYS)

    events = list_events(time_min=window_start, time_max=window_end, max_results=50)

    title_lower = title.lower()
    title_keywords = _extract_keywords(title)

    matches = []
    for event in events:
        summary = event.get("summary", "")
        summary_lower = summary.lower()

        if title_lower in summary_lower:
            matches.append(event)
            continue

        summary_keywords = _extract_keywords(summary)
        if title_keywords and title_keywords & summary_keywords:
            matches.append(event)

    return matches


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
        if action == "listar":
            return self._handle_list(extraction, now, tz)

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

    def _handle_list(self, extraction: dict, now: datetime, tz: ZoneInfo) -> SkillResult:
        date_expression = extraction.get("date_expression")

        if date_expression:
            target_date = resolve_date(date_expression, now)
        else:
            target_date = None

        if target_date is not None:
            # Se pidió un día concreto: rango de ese día completo
            window_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            window_end = window_start + timedelta(days=1)
        else:
            # No se reconoció fecha concreta (o pidieron "esta semana"/no dijeron nada):
            # rango por defecto de los próximos 7 días
            window_start = now
            window_end = now + timedelta(days=7)

        try:
            events = list_events(time_min=window_start, time_max=window_end, max_results=20)
        except Exception:
            return SkillResult(success=False, message="Ha habido un problema al consultar tu calendario.")

        if not events:
            return SkillResult(success=True, message="No tienes ningún evento en ese periodo.", data={"events": []})

        lineas = []
        for event in events:
            titulo = event.get("summary", "(sin título)")
            inicio = event["start"].get("dateTime", event["start"].get("date"))
            fecha_legible = datetime.fromisoformat(inicio).strftime("%d/%m a las %H:%M") if "T" in inicio else inicio
            lineas.append(f"- {titulo} ({fecha_legible})")

        mensaje = "Esto es lo que tienes:\n" + "\n".join(lineas)
        return SkillResult(success=True, message=mensaje, data={"events": events})