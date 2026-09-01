# skills/calendar/skill.py

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config.settings import TIMEZONE
from services.llm.llm_response import generate_response_text
from services.llm.llm_extract_calendar import extract_calendar_intent
from services.gemini_fallback import extract_calendar_intent_fallback
from services.date_resolver import resolve_date, resolve_structured_time
from services.google_calendar import list_events, create_event, update_event, delete_event
from skills.base import Skill, SkillResult

DEFAULT_EVENT_DURATION_HOURS = 1
SEARCH_WINDOW_DAYS = 30

STOPWORDS = {"el", "la", "los", "las", "de", "del", "un", "una", "con", "y", "a", "en"}


def _is_valid_extraction(result: dict | None, original_order: str = "") -> bool:
    if result is None:
        return False

    action = result.get("action")
    if action not in ("crear", "actualizar", "eliminar", "listar"):
        return False

    if action in ("crear", "actualizar"):
        has_date = result.get("date_expression") or result.get("resolved_date")
        if not has_date and not result.get("time"):
            return False

    if action == "crear":
        title = result.get("title")
        if not title:
            return False
        if original_order and title.strip().lower() == original_order.strip().lower():
            return False

    return True


def _resolve_base_date(extraction: dict, now: datetime, tz: ZoneInfo) -> datetime | None:
    """Obtiene el datetime base, soportando tanto 'date_expression' (extractor
    local, texto libre) como 'resolved_date' (fallback Gemini, ya calculada)."""
    if extraction.get("resolved_date"):
        try:
            return datetime.fromisoformat(extraction["resolved_date"]).replace(tzinfo=tz)
        except ValueError:
            return None

    date_expression = extraction.get("date_expression")
    if date_expression:
        return resolve_date(date_expression, now)

    return now


def _combine_date_and_time(base_date: datetime, time_obj: dict | None, tz: ZoneInfo) -> datetime | None:
    if time_obj is None:
        return base_date.replace(tzinfo=tz)
    resolved_time = resolve_structured_time(time_obj)
    if resolved_time is None:
        return None
    return datetime.combine(base_date.date(), resolved_time, tzinfo=tz)


def _extract_keywords(text: str) -> set[str]:
    words = text.lower().split()
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _find_event_by_title(title: str, now: datetime) -> list[dict]:
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


def _build_message(fallback_message: str, info: dict) -> str:
    """Intenta generar una respuesta natural con el LLM local; si falla,
    usa la plantilla fija. Los mensajes de error NUNCA pasan por el LLM --
    el riesgo de alucinación es mayor con menos datos concretos, y una
    plantilla clara es preferible a una redacción 'natural' arriesgada."""
    if info.get("resultado") == "error":
        return fallback_message
    
    natural = generate_response_text(info)
    return natural if natural else fallback_message


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

        tz = ZoneInfo(TIMEZONE)
        now = datetime.now(tz)

        extraction = extract_calendar_intent(order)

        if not _is_valid_extraction(extraction, original_order=order):
            extraction = extract_calendar_intent_fallback(order, now)

            if not _is_valid_extraction(extraction, original_order=order):
                return SkillResult(success=False, message="No he entendido bien la orden, ¿puedes repetirla de otra forma?")

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
        base_date = _resolve_base_date(extraction, now, tz)

        if base_date is None:
            fallback = "No he entendido bien cuándo quieres el evento."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "crear", "resultado": "error", "motivo": "fecha no reconocida",
            }))

        start = _combine_date_and_time(base_date, extraction.get("time"), tz)

        if start is None:
            fallback = "No he entendido bien la hora que me has dicho."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "crear", "resultado": "error", "motivo": "hora no reconocida",
            }))

        end = start + timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)

        try:
            event = create_event(summary=extraction["title"], start=start, end=end)
        except Exception:
            fallback = "Ha habido un problema al crear el evento en tu calendario."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "crear", "resultado": "error", "motivo": "fallo al conectar con Google Calendar",
            }))

        fecha_legible = start.strftime("%d/%m a las %H:%M")
        fallback = f"Hecho, he creado '{extraction['title']}' el {fecha_legible}."
        message = _build_message(fallback, {
            "accion": "crear", "resultado": "exito",
            "titulo": extraction["title"], "fecha": start.strftime("%Y-%m-%d"), "hora": start.strftime("%H:%M"),
        })

        return SkillResult(success=True, message=message, data={"event_id": event["id"]})

    def _handle_delete(self, extraction: dict, now: datetime, tz: ZoneInfo) -> SkillResult:
        title = extraction.get("title")
        if not title:
            fallback = "No sé qué evento quieres cancelar, dime el título."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "eliminar", "resultado": "error", "motivo": "sin título especificado",
            }))

        matches = _find_event_by_title(title, now)

        if not matches:
            fallback = f"No he encontrado ningún evento llamado '{title}'."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "eliminar", "resultado": "error", "motivo": "evento no encontrado", "titulo_buscado": title,
            }))

        if len(matches) > 1:
            fallback = f"He encontrado varios eventos parecidos a '{title}', sé más específico."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "eliminar", "resultado": "error", "motivo": "varios eventos coinciden", "titulo_buscado": title,
                "cantidad_encontrada": len(matches),
            }))

        event = matches[0]

        try:
            delete_event(event["id"])
        except Exception:
            fallback = "Ha habido un problema al cancelar el evento."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "eliminar", "resultado": "error", "motivo": "fallo al conectar con Google Calendar",
            }))

        fallback = f"Hecho, he cancelado '{title}'."
        message = _build_message(fallback, {
            "accion": "eliminar", "resultado": "exito", "titulo": title,
        })

        return SkillResult(success=True, message=message)

    def _handle_update(self, extraction: dict, now: datetime, tz: ZoneInfo) -> SkillResult:
        title = extraction.get("title")
        if not title:
            fallback = "No sé qué evento quieres mover, dime el título."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "actualizar", "resultado": "error", "motivo": "sin título especificado",
            }))

        matches = _find_event_by_title(title, now)

        if not matches:
            fallback = f"No he encontrado ningún evento llamado '{title}'."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "actualizar", "resultado": "error", "motivo": "evento no encontrado", "titulo_buscado": title,
            }))

        if len(matches) > 1:
            fallback = f"He encontrado varios eventos parecidos a '{title}', sé más específico."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "actualizar", "resultado": "error", "motivo": "varios eventos coinciden", "titulo_buscado": title,
                "cantidad_encontrada": len(matches),
            }))

        event = matches[0]

        base_date = _resolve_base_date(extraction, now, tz)
        if base_date is None:
            fallback = "No he entendido bien cuándo quieres mover el evento."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "actualizar", "resultado": "error", "motivo": "fecha no reconocida",
            }))

        new_start = _combine_date_and_time(base_date, extraction.get("time"), tz)

        if new_start is None:
            fallback = "No he entendido bien la nueva hora que me has dicho."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "actualizar", "resultado": "error", "motivo": "hora no reconocida",
            }))

        new_end = new_start + timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)

        try:
            update_event(event["id"], start=new_start, end=new_end)
        except Exception:
            fallback = "Ha habido un problema al mover el evento."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "actualizar", "resultado": "error", "motivo": "fallo al conectar con Google Calendar",
            }))

        fecha_legible = new_start.strftime("%d/%m a las %H:%M")
        fallback = f"Hecho, he movido '{title}' al {fecha_legible}."
        message = _build_message(fallback, {
            "accion": "actualizar", "resultado": "exito", "titulo": title,
            "nueva_fecha": new_start.strftime("%Y-%m-%d"), "nueva_hora": new_start.strftime("%H:%M"),
        })

        return SkillResult(success=True, message=message)

    def _handle_list(self, extraction: dict, now: datetime, tz: ZoneInfo) -> SkillResult:
        date_expression = extraction.get("date_expression")
        target_date = resolve_date(date_expression, now) if date_expression else None

        if target_date is not None:
            window_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            window_end = window_start + timedelta(days=1)
        else:
            window_start = now
            window_end = now + timedelta(days=7)

        try:
            events = list_events(time_min=window_start, time_max=window_end, max_results=20)
        except Exception:
            fallback = "Ha habido un problema al consultar tu calendario."
            return SkillResult(success=False, message=_build_message(fallback, {
                "accion": "listar", "resultado": "error", "motivo": "fallo al conectar con Google Calendar",
            }))

        if not events:
            fallback = "No tienes ningún evento en ese periodo."
            message = _build_message(fallback, {
                "accion": "listar", "resultado": "exito", "eventos": [],
            })
            return SkillResult(success=True, message=message, data={"events": []})

        eventos_info = []
        for event in events:
            titulo = event.get("summary", "(sin título)")
            inicio = event["start"].get("dateTime", event["start"].get("date"))
            eventos_info.append({"titulo": titulo, "inicio": inicio})

        lineas = [f"- {e['titulo']} ({e['inicio']})" for e in eventos_info]
        fallback = "Esto es lo que tienes:\n" + "\n".join(lineas)

        message = _build_message(fallback, {
            "accion": "listar", "resultado": "exito", "eventos": eventos_info,
        })

        return SkillResult(success=True, message=message, data={"events": events})