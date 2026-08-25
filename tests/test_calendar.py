from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.google_calendar import *

tz = ZoneInfo("Europe/Madrid")
ahora = datetime.now(tz)

def test_list():
    """Comprobación de listado"""
    en_una_semana = ahora + timedelta(days=7)
    eventos = list_events(time_min=ahora, time_max=en_una_semana)

    assert len(eventos) == 1

def test_create():
    """Comprobación de creación"""
    inicio = ahora + timedelta(days=1)
    fin = inicio + timedelta(hours=1)

    en_una_semana = ahora + timedelta(days=7)
    eventos_actuales = list_events(time_min=ahora, time_max=en_una_semana)

    nuevo = create_event(
        summary="Prueba tests",
        start=inicio,
        end=fin,
        description="Evento de prueba creado desde el script de test",
    )
    eventos_nuevos = list_events(time_min=ahora, time_max=en_una_semana)

    assert len(eventos_actuales) + 1 == len(eventos_nuevos)

def test_update():
    """Comprobación de actualización"""
    inicio = ahora + timedelta(days=1)
    fin = inicio + timedelta(hours=1)

    nuevo = create_event(
        summary="Prueba tests",
        start=inicio,
        end=fin,
        description="Evento de prueba creado desde el script de test para actualizar",
    )
    event_id = nuevo['id']

    update_event(event_id, description = "Actualizacion del evento")

    assert get_event(event_id)['description'] == "Actualizacion del evento"
