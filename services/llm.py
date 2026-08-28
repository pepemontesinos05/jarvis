import json
import requests

from config.settings import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = """Eres un extractor de datos. Tu única tarea es leer una orden en español sobre un calendario y devolver un JSON con esta forma exacta, sin texto adicional, sin explicaciones, sin markdown:

{"action": "crear"|"actualizar"|"eliminar"|"listar"|"desconocido", "title": string|null, "date_expression": string|null, "time": {"hour": int|null, "minute": int, "modifier": "exacta"|"mas"|"menos", "period": "mañana"|"tarde"|"noche"|null}|null}

Reglas:
- "action" es "crear" si se pide añadir/poner un evento nuevo.
- "action" es "eliminar" si se pide cancelar/borrar un evento.
- "action" es "actualizar" si se pide mover/cambiar un evento existente.
- "action" es "listar" si se pregunta qué eventos hay, qué tiene agendado, o similar
  (ej: "qué tengo mañana", "dime mis eventos de esta semana", "tengo algo el jueves").
- "title" debe conservar el nombre del evento tal como lo dice el usuario, incluyendo
  varias palabras si las usa (ej: "reunión de seguimiento del proyecto"). NO lo resumas
  a una sola palabra genérica salvo que el usuario solo haya dicho una palabra.
- Para "listar", "title" siempre es null (no se busca un evento concreto, se listan todos).
- "date_expression" es el texto EXACTO tal como aparece en la orden (ej: "mañana", "esta semana", "el jueves"), SIN convertirlo tú mismo a una fecha real. NUNCA inventes un año o fecha calculada.
- "time.hour" es la hora tal como se dice (1-12 o 0-23 según se diga), SIN convertir tú mismo a formato 24h. Esa conversión la hace otro sistema después.
- "time.modifier" es "mas" para minutos que se suman (ej: "y veinte"), "menos" para minutos que se restan (ej: "menos cuarto"), "exacta" si no hay fracción.
- Si algún dato no aparece, su valor es null.

Ejemplo 1:
Orden: "pon dentista mañana a las nueve y veinte de la noche"
{"action": "crear", "title": "dentista", "date_expression": "mañana", "time": {"hour": 9, "minute": 20, "modifier": "mas", "period": "noche"}}

Ejemplo 2:
Orden: "cancela la reunión del jueves"
{"action": "eliminar", "title": "reunión", "date_expression": "el jueves", "time": null}

Ejemplo 3:
Orden: "mueve el entrenamiento a las siete menos cuarto"
{"action": "actualizar", "title": "entrenamiento", "date_expression": null, "time": {"hour": 7, "minute": 15, "modifier": "menos", "period": null}}

Ejemplo 4:
Orden: "mueve la reunión de seguimiento del proyecto a las 6 de la tarde"
{"action": "actualizar", "title": "reunión de seguimiento del proyecto", "date_expression": null, "time": {"hour": 6, "minute": 0, "modifier": "exacta", "period": "tarde"}}

Ejemplo 5:
Orden: "qué tengo mañana"
{"action": "listar", "title": null, "date_expression": "mañana", "time": null}

Ejemplo 6:
Orden: "dime todos los eventos que tengo esta semana"
{"action": "listar", "title": null, "date_expression": "esta semana", "time": null}
"""

def extract_calendar_intent(order: str, timeout: int = 12):
    """Envía una orden en español al LLM local y devuelve el JSON estructurado.

    Devuelve None si el modelo no responde, tarda demasiado, o su respuesta
    no es un JSON válido -- en cualquiera de esos casos, la skill que llame
    a esta función debe tratarlo como "no se pudo entender la orden".
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f'Orden: "{order}"'},
        ],
        "stream": False,
    }

    try:
        response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return None

    content = response.json().get("message", {}).get("content", "")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None