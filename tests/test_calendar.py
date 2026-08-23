from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.google_calendar import list_events

tz = ZoneInfo("Europe/Madrid")
ahora = datetime.now(tz)
en_una_semana = ahora + timedelta(days=7)

eventos = list_events(time_min=ahora, time_max=en_una_semana)

print(f"Encontrados {len(eventos)} eventos en los próximos 7 días:\n")

for evento in eventos:
    titulo = evento.get("summary", "(sin título)")
    inicio = evento["start"].get("dateTime", evento["start"].get("date"))
    print(f"- {titulo} → {inicio}")