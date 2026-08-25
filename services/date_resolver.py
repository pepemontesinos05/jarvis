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
    """
    Convertir expresiones a fechas
    Si no encuentra, devolver un None.
    """

    if not expression:
        return None

    expression = expression.lower().strip()

    # Eliminar articulos
    expression = re.sub(r"^(el|la|los|las)\s+", "", expression)

    if expression == "hoy":
        return now

    if expression == "mañana":
        return now + timedelta(days=1)

    if expression == "pasado mañana":
        return now + timedelta(days=2)

    # "en 3 días", "dentro de 5 días"
    match = re.search(r"(?:en|dentro de)\s+(\d+)\s+días?", expression)

    if match:
        days = int(match.group(1))
        return now + timedelta(days=days)

    # Dias
    for index, weekday in enumerate(WEEKDAYS):
        if weekday in expression:
            days_until = (index - now.weekday()) % 7

            # Interpretar dias restantes si el dia es el mismo que hoy
            if days_until == 0:
                days_until = 7

            return now + timedelta(days=days_until)

    return None


def _apply_period(hour: int, expression: str) -> int | None:
    if not 0 <= hour <= 23:
        return None

    if "de la mañana" in expression:
        if hour == 12:
            return 0

    elif "de la tarde" in expression or "de la noche" in expression:
        if 1 <= hour <= 11:
            hour += 12

    return hour

def resolve_time(expression: str) -> time | None:
    if not expression:
        return None

    expression = expression.lower().strip()

    # 17:30
    match = re.search(r"\b(\d{1,2}):(\d{2})\b", expression)

    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        return time(hour=hour, minute=minute)

    # "las 5 y media"
    match = re.search(r"\b(\d{1,2})\s+y\s+media\b", expression)

    if match:
        hour = int(match.group(1))
        minute = 30

        hour = _apply_period(hour, expression)

        if hour is None:
            return None

        return time(hour=hour, minute=minute)

    # "las 7 y cuarto"
    match = re.search(r"\b(\d{1,2})\s+y\s+cuarto\b", expression)

    if match:
        hour = int(match.group(1))
        minute = 15

        hour = _apply_period(hour, expression)

        if hour is None:
            return None

        return time(hour=hour, minute=minute)

    # "las 6 menos cuarto" -> 05:45
    match = re.search(r"\b(\d{1,2})\s+menos\s+cuarto\b", expression)

    if match:
        hour = int(match.group(1))

        # Hay que tener en cuenta que primero hay que determinar si son 00 o 12
        hour = _apply_period(hour, expression)

        hour -= 1

        if hour < 0:
            hour = 23

        if hour is None:
            return None

        return time(hour=hour, minute=45)

    # "las 5", "a las 17"
    match = re.search(r"\b(\d{1,2})\b", expression)

    if match:
        hour = int(match.group(1))

        hour = _apply_period(hour, expression)

        if hour is None:
            return None

        return time(hour=hour, minute=0)

    return None