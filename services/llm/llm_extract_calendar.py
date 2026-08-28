import json
import requests
from config.settings import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = """Eres un extractor de datos. Tu única tarea es leer una orden en español sobre un calendario y devolver un JSON con esta forma exacta, sin texto adicional, sin explicaciones, sin markdown:

{"action": "crear"|"actualizar"|"eliminar"|"listar"|"desconocido", "title": string|null, "date_expression": string|null, "time": {"hour": int|null, "minute": int, "modifier": "exacta"|"mas"|"menos", "period": "mañana"|"tarde"|"noche"|null}|null}

Reglas:
- "action" es "crear" si se pide añadir/poner un evento nuevo.
- "action" es "eliminar" si se pide cancelar/borrar un evento.
- "action" es "actualizar" si se pide mover/cambiar un evento existente.
- "action" es "listar" si se pregunta qué eventos hay, qué tiene agendado, o similar.
- "title" debe conservar el nombre del evento tal como lo dice el usuario, incluyendo
  varias palabras si las usa. NO lo resumas a una sola palabra genérica salvo que el
  usuario solo haya dicho una palabra.
- Para "listar", "title" siempre es null.
- "date_expression" es el texto EXACTO tal como aparece en la orden, SIN convertirlo tú mismo a una fecha real. NUNCA inventes un año o fecha calculada.
- "time.hour" es la hora tal como se dice (1-12 o 0-23 según se diga), SIN convertir tú mismo a formato 24h.
- "time.period" es "mañana"/"tarde"/"noche" si se menciona explícitamente esa parte del día (ej: "de la mañana", "de la tarde", "de la noche"). Si no se menciona ningún periodo, es null -- NUNCA lo dejes null solo porque la construcción de la frase es simple.
- "time.modifier" es "mas" para minutos que se suman, "menos" para minutos que se restan, "exacta" si no hay fracción.
- Si algún dato no aparece, su valor es null.

Ejemplo 1 (hora simple + periodo):
Orden: "pon reunión el lunes a las 4 de la mañana"
{"action": "crear", "title": "reunión", "date_expression": "el lunes", "time": {"hour": 4, "minute": 0, "modifier": "exacta", "period": "mañana"}}

Ejemplo 2 (hora + fracción "y" + periodo):
Orden: "pon dentista mañana a las nueve y veinte de la noche"
{"action": "crear", "title": "dentista", "date_expression": "mañana", "time": {"hour": 9, "minute": 20, "modifier": "mas", "period": "noche"}}

Ejemplo 3 (hora + "menos" + periodo):
Orden: "mueve el entrenamiento a las siete menos cuarto de la tarde"
{"action": "actualizar", "title": "entrenamiento", "date_expression": null, "time": {"hour": 7, "minute": 15, "modifier": "menos", "period": "tarde"}}

Ejemplo 4 (hora + "menos" sin periodo):
Orden: "mueve el entrenamiento a las siete menos cuarto"
{"action": "actualizar", "title": "entrenamiento", "date_expression": null, "time": {"hour": 7, "minute": 15, "modifier": "menos", "period": null}}

Ejemplo 5 (título compuesto, varias palabras):
Orden: "mueve la reunión de seguimiento del proyecto a las 6 de la tarde"
{"action": "actualizar", "title": "reunión de seguimiento del proyecto", "date_expression": null, "time": {"hour": 6, "minute": 0, "modifier": "exacta", "period": "tarde"}}

Ejemplo 6 (cancelar):
Orden: "cancela la reunión del jueves"
{"action": "eliminar", "title": "reunión", "date_expression": "el jueves", "time": null}

Ejemplo 7 ("en punto"):
Orden: "pon llamada con el banco mañana a las 9 en punto de la mañana"
{"action": "crear", "title": "llamada con el banco", "date_expression": "mañana", "time": {"hour": 9, "minute": 0, "modifier": "exacta", "period": "mañana"}}

Ejemplo 8 (mediodía/medianoche, sin hora numérica):
Orden: "pon comida con mis padres el sábado a mediodía"
{"action": "crear", "title": "comida con mis padres", "date_expression": "el sábado", "time": {"hour": 12, "minute": 0, "modifier": "exacta", "period": null}}

Ejemplo 9 (consultar/listar):
Orden: "qué tengo mañana"
{"action": "listar", "title": null, "date_expression": "mañana", "time": null}

Ejemplo 10 ("y diez/veinte/veinticinco" + periodo):
Orden: "pon cena a las ocho y veinte de la noche"
{"action": "crear", "title": "cena", "date_expression": null, "time": {"hour": 8, "minute": 20, "modifier": "mas", "period": "noche"}}
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