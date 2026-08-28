import json
from datetime import datetime
from google import genai
from config.settings import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

FALLBACK_PROMPT_TEMPLATE = """Eres un extractor de datos para un asistente de calendario. Hoy es {fecha_hoy} ({dia_semana}).

Lee esta orden en español y devuelve SOLO un JSON con esta forma exacta, sin texto adicional, sin explicaciones, sin markdown:

{{"action": "crear"|"actualizar"|"eliminar"|"listar"|"desconocido", "title": string|null, "resolved_date": "YYYY-MM-DD"|null, "time": {{"hour": int|null, "minute": int, "modifier": "exacta"|"mas"|"menos", "period": "mañana"|"tarde"|"noche"|null}}|null}}

Reglas:
- "title" debe conservar el nombre del evento tal como lo dice el usuario, con varias palabras si las usa.
- "resolved_date" es la fecha YA CALCULADA a partir de la expresión temporal de la orden (ej: si hoy es {fecha_hoy} y dicen "el finde que viene", calcula tú mismo qué fecha exacta es el próximo sábado). Este es precisamente tu trabajo aquí: resolver expresiones de fecha complejas que un sistema más simple no pudo interpretar.
- "time.hour" es la hora tal como se dice, SIN convertir tú mismo a formato 24h.
- Si algún dato no aparece, su valor es null.

Orden: "{orden}"
"""


def extract_calendar_intent_fallback(order: str, now: datetime, timeout: int = 15) -> dict | None:
    """Fallback a Gemini para órdenes que el extractor local (Ollama) no pudo
    resolver con confianza. Devuelve None si falla la llamada o el formato.

    A diferencia de extract_calendar_intent (local), este devuelve
    'resolved_date' (YYYY-MM-DD ya calculada) en vez de 'date_expression'
    (texto libre) -- Gemini, al ser un modelo grande, es fiable haciendo
    la aritmética de fechas que el resolver local no puede cubrir.
    """
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    prompt = FALLBACK_PROMPT_TEMPLATE.format(
        fecha_hoy=now.strftime("%Y-%m-%d"),
        dia_semana=dias[now.weekday()],
        orden=order,
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt,
        )
    except Exception:
        return None

    content = (response.text or "").strip()

    if content.startswith("```"):
        content = content.strip("`")
        content = content.replace("json\n", "", 1).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None