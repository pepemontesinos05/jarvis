import re
from datetime import datetime, timedelta, time


WEEKDAYS = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]


def resolve_date(expression: str, now: datetime):
    """Convertir expresiones de fecha en español a datetime. None si no se reconoce."""

    if not expression:
        return None

    expression = expression.lower().strip()
    expression = re.sub(r"^(el|la|los|las)\s+", "", expression)

    if expression == "hoy":
        return now

    if expression == "mañana":
        return now + timedelta(days=1)

    if expression == "pasado mañana":
        return now + timedelta(days=2)

    match = re.search(r"(?:en|dentro de)\s+(\d+)\s+días?", expression)
    if match:
        return now + timedelta(days=int(match.group(1)))
    
    days = "|".join(WEEKDAYS)
    match = (
        re.search(rf"({days})\s+(?:que viene|próximo|siguiente)", expression)
        or re.search(rf"próximo\s+({days})", expression)
        or re.search(rf"({days})\s+de la semana que viene", expression)
    )
    if match:
        day_founded = match.group(1)
        index = WEEKDAYS.index(day_founded)
        days_until = (len(WEEKDAYS) - 1 - now.weekday()) + (index + 1)
        return now + timedelta(days=days_until)

    for index, weekday in enumerate(WEEKDAYS):
        if weekday in expression:
            days_until = (index - now.weekday()) % 7
            if days_until == 0:
                days_until = 7
            return now + timedelta(days=days_until)

    return None


# ---------------------------------------------------------------------------
# Helpers internos de hora
# ---------------------------------------------------------------------------

def _detect_period(expression: str):
    """Detecta el periodo del día a partir de texto libre."""
    if "de la mañana" in expression:
        return "mañana"
    if "de la tarde" in expression:
        return "tarde"
    if "de la noche" in expression:
        return "noche"
    return None


def _apply_period(hour: int, period: str | None):
    """Convierte una hora de 12h + periodo del día a formato 24h.

    period: "mañana" | "tarde" | "noche" | None

    Nota: puede devolver 24 para "12 de la noche" -> se resuelve correctamente
    en _build_time (24:00 se normaliza a 00:00), en vez de intentar forzar
    aquí un caso especial que rompería la resta de minutos posterior.
    """
    if not 0 <= hour <= 23:
        return None

    if period is None or period == "mañana":
        return hour

    if period == "tarde":
        return hour + 12 if 1 <= hour <= 11 else hour

    if period == "noche":
        if hour == 12:
            return 24
        return hour + 12 if 1 <= hour <= 11 else hour

    return hour


def _build_time(hour: int, minute: int):
    """Normaliza hour*60+minute (puede ser negativo o >59) a un time válido.

    Esto es lo que permite que "menos cuarto"/"menos veinte" se resuelvan
    con una sola resta de minutos, sin tener que ajustar 'hour' a mano
    ni tratar el cruce de medianoche como caso especial.
    """
    total_minutes = (hour * 60 + minute) % (24 * 60)
    return time(hour=total_minutes // 60, minute=total_minutes % 60)


# ---------------------------------------------------------------------------
# Resolver de hora (texto libre en formato numérico, sin números en palabras)
# ---------------------------------------------------------------------------

def resolve_time(expression: str):
    if not expression:
        return None

    expr = expression.lower().strip()

    if "mediodía" in expr or "mediodia" in expr:
        return time(hour=12, minute=0)
    if "medianoche" in expr:
        return time(hour=0, minute=0)

    # HH:MM explícito. Si aparece ':', tratamos SIEMPRE este formato:
    # si los valores no son válidos (24:00, 12:60), devolvemos None
    # en vez de intentar reinterpretar el texto de otra forma.
    if ":" in expr:
        match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", expr)
        return time(int(match.group(1)), int(match.group(2))) if match else None

    period = _detect_period(expr)

    match = re.search(r"\b(\d{1,2})\s+y\s+media\b", expr)
    if match:
        hour = _apply_period(int(match.group(1)), period)
        return _build_time(hour, 30) if hour is not None else None

    match = re.search(r"\b(\d{1,2})\s+y\s+cuarto\b", expr)
    if match:
        hour = _apply_period(int(match.group(1)), period)
        return _build_time(hour, 15) if hour is not None else None

    for palabra, minutos in (("veinticinco", 25), ("veinte", 20), ("diez", 10)):
        match = re.search(rf"\b(\d{{1,2}})\s+y\s+{palabra}\b", expr)
        if match:
            hour = _apply_period(int(match.group(1)), period)
            return _build_time(hour, minutos) if hour is not None else None

    match = re.search(r"\b(\d{1,2})\s+menos\s+cuarto\b", expr)
    if match:
        hour = _apply_period(int(match.group(1)), period)
        return _build_time(hour, -15) if hour is not None else None

    for palabra, minutos in (("veinticinco", 25), ("veinte", 20), ("diez", 10)):
        match = re.search(rf"\b(\d{{1,2}})\s+menos\s+{palabra}\b", expr)
        if match:
            hour = _apply_period(int(match.group(1)), period)
            return _build_time(hour, -minutos) if hour is not None else None

    match = re.search(r"\b(\d{1,2})\s+en\s+punto\b", expr)
    if match:
        hour = _apply_period(int(match.group(1)), period)
        return _build_time(hour, 0) if hour is not None else None

    match = re.search(r"\b(\d{1,2})\b", expr)
    if match:
        hour = _apply_period(int(match.group(1)), period)
        return _build_time(hour, 0) if hour is not None else None

    return None


# ---------------------------------------------------------------------------
# Resolver estructurado (uso real: salida del extractor LLM)
# ---------------------------------------------------------------------------

def resolve_structured_time(time_obj: dict | None) -> time | None:
    """time_obj = {"hour": int, "minute": int, "modifier": "exacta"|"mas"|"menos",
                    "period": "mañana"|"tarde"|"noche"|None}"""
    if not time_obj:
        return None

    hour = time_obj.get("hour")
    if hour is None:
        return None

    minute = time_obj.get("minute") or 0
    modifier = time_obj.get("modifier", "exacta")
    period = time_obj.get("period")

    hour_24 = _apply_period(hour, period)
    if hour_24 is None:
        return None

    signed_minute = -minute if modifier == "menos" else minute
    return _build_time(hour_24, signed_minute)