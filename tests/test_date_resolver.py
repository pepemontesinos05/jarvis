from datetime import datetime, time

import pytest

from services.date_resolver import resolve_date, resolve_time


NOW = datetime(2026, 8, 25, 10, 0)  # Tuesday


# ============================================================
# DATE TESTS
# ============================================================

@pytest.mark.parametrize(
    "expression, expected",
    [
        # Basic relative dates
        ("hoy", datetime(2026, 8, 25).date()),
        ("mañana", datetime(2026, 8, 26).date()),
        ("pasado mañana", datetime(2026, 8, 27).date()),

        # Relative number of days
        ("en 1 día", datetime(2026, 8, 26).date()),
        ("en 3 días", datetime(2026, 8, 28).date()),
        ("en 0 días", datetime(2026, 8, 25).date()),
        ("dentro de 1 día", datetime(2026, 8, 26).date()),
        ("dentro de 5 días", datetime(2026, 8, 30).date()),

        # Weekdays
        ("jueves", datetime(2026, 8, 27).date()),
        ("el jueves", datetime(2026, 8, 27).date()),
        ("sábado", datetime(2026, 8, 29).date()),
        ("el lunes", datetime(2026, 8, 31).date()),

        # Today is Tuesday, so "martes" means next Tuesday
        ("martes", datetime(2026, 9, 1).date()),
        ("el martes", datetime(2026, 9, 1).date()),

        # Normalization
        ("  mañana  ", datetime(2026, 8, 26).date()),
        ("MAÑANA", datetime(2026, 8, 26).date()),
        ("EL JUEVES", datetime(2026, 8, 27).date()),
    ],
)
def test_resolve_date_valid(expression, expected):
    result = resolve_date(expression, NOW)

    assert result is not None
    assert result.date() == expected


@pytest.mark.parametrize(
    "expression",
    [
        "",
        None,
        "algo random",
        "el día que pueda",
        "algún día",
        "en tres días",       # Number in words -> Gemini for now
        "la semana que viene",
        "el mes que viene",
        "ayer",
    ],
)
def test_resolve_date_unknown(expression):
    assert resolve_date(expression, NOW) is None


# ============================================================
# NUMERIC TIME TESTS
# ============================================================

@pytest.mark.parametrize(
    "expression, expected",
    [
        ("17:00", time(17, 0)),
        ("17:30", time(17, 30)),
        ("a las 17:30", time(17, 30)),
        ("a las 9:05", time(9, 5)),
        ("las 5", time(5, 0)),
        ("a las 7", time(7, 0)),
        ("a las 17", time(17, 0)),
        ("0:00", time(0, 0)),
        ("23:59", time(23, 59)),
    ],
)
def test_resolve_numeric_time(expression, expected):
    assert resolve_time(expression) == expected


# ============================================================
# MORNING / AFTERNOON / NIGHT
# ============================================================

@pytest.mark.parametrize(
    "expression, expected",
    [
        ("9 de la mañana", time(9, 0)),
        ("a las 9 de la mañana", time(9, 0)),
        ("5 de la tarde", time(17, 0)),
        ("a las 5 de la tarde", time(17, 0)),
        ("7 de la tarde", time(19, 0)),
        ("9 de la noche", time(21, 0)),
        ("a las 11 de la noche", time(23, 0)),

        # Noon / midnight
        ("12 de la mañana", time(12, 0)),
        ("12 de la tarde", time(12, 0)),
        ("12 de la noche", time(0, 0)),
    ],
)
def test_resolve_time_period(expression, expected):
    assert resolve_time(expression) == expected


# ============================================================
# "MAÑANA" AMBIGUITY
# ============================================================

def test_manana_as_date():
    result = resolve_date("mañana", NOW)

    assert result.date() == datetime(2026, 8, 26).date()


def test_manana_as_part_of_time():
    result = resolve_time("a las 9 de la mañana")

    assert result == time(9, 0)


# ============================================================
# HALF PAST
# ============================================================

@pytest.mark.parametrize(
    "expression, expected",
    [
        ("las 5 y media", time(5, 30)),
        ("5 y media", time(5, 30)),
        ("las 9 y media", time(9, 30)),
        ("5 y media de la tarde", time(17, 30)),
        ("las 7 y media de la tarde", time(19, 30)),
        ("9 y media de la noche", time(21, 30)),
        ("9 y media de la mañana", time(9, 30)),
    ],
)
def test_resolve_half_past(expression, expected):
    assert resolve_time(expression) == expected


# ============================================================
# QUARTER PAST
# ============================================================

@pytest.mark.parametrize(
    "expression, expected",
    [
        ("las 5 y cuarto", time(5, 15)),
        ("5 y cuarto", time(5, 15)),
        ("7 y cuarto de la mañana", time(7, 15)),
        ("5 y cuarto de la tarde", time(17, 15)),
        ("9 y cuarto de la noche", time(21, 15)),
    ],
)
def test_resolve_quarter_past(expression, expected):
    assert resolve_time(expression) == expected


# ============================================================
# QUARTER TO
# ============================================================

@pytest.mark.parametrize(
    "expression, expected",
    [
        ("las 6 menos cuarto", time(5, 45)),
        ("6 menos cuarto", time(5, 45)),
        ("9 menos cuarto de la mañana", time(8, 45)),
        ("6 menos cuarto de la tarde", time(17, 45)),
        ("10 menos cuarto de la noche", time(21, 45)),

        # Important edge cases
        ("1 menos cuarto de la mañana", time(0, 45)),
        ("12 menos cuarto de la mañana", time(11, 45)),
        ("12 menos cuarto de la noche", time(23, 45)),
    ],
)
def test_resolve_quarter_to(expression, expected):
    assert resolve_time(expression) == expected


# ============================================================
# OTHER COMMON MINUTES
# ============================================================

@pytest.mark.parametrize(
    "expression, expected",
    [
        ("5 y diez", time(5, 10)),
        ("5 y veinte", time(5, 20)),
        ("5 y veinticinco", time(5, 25)),
        ("5 y diez de la tarde", time(17, 10)),
        ("7 y veinte de la noche", time(19, 20)),

        ("6 menos diez", time(5, 50)),
        ("6 menos veinte", time(5, 40)),
        ("6 menos veinticinco", time(5, 35)),
        ("6 menos diez de la tarde", time(17, 50)),
    ],
)
def test_resolve_other_minutes(expression, expected):
    assert resolve_time(expression) == expected


# ============================================================
# "EN PUNTO"
# ============================================================

@pytest.mark.parametrize(
    "expression, expected",
    [
        ("las 5 en punto", time(5, 0)),
        ("9 en punto", time(9, 0)),
        ("5 en punto de la tarde", time(17, 0)),
        ("9 en punto de la noche", time(21, 0)),
    ],
)
def test_resolve_exact_hour(expression, expected):
    assert resolve_time(expression) == expected


# ============================================================
# NOON / MIDNIGHT
# ============================================================

def test_resolve_noon():
    assert resolve_time("mediodía") == time(12, 0)


def test_resolve_midnight():
    assert resolve_time("medianoche") == time(0, 0)


# ============================================================
# INVALID TIMES
# ============================================================

@pytest.mark.parametrize(
    "expression",
    [
        "",
        None,
        "hora desconocida",
        "27:80",
        "24:00",
        "12:60",
        "99",
        "a cualquier hora",
    ],
)
def test_resolve_invalid_time(expression):
    assert resolve_time(expression) is None


# ============================================================
# EXPRESSIONS THAT SHOULD GO TO GEMINI
# ============================================================

@pytest.mark.parametrize(
    "expression",
    [
        "cinco y media",
        "siete menos cuarto",
        "sobre las seis",
        "a eso de las nueve",
        "seis y pico",
        "por la tarde",
        "por la mañana",
    ],
)
def test_resolve_complex_time_falls_back(expression):
    assert resolve_time(expression) is None