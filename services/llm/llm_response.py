import json
import requests
from config.settings import OLLAMA_HOST, OLLAMA_MODEL

RESPONSE_SYSTEM_PROMPT = """Eres un redactor de confirmaciones para un asistente de calendario. Se te da un JSON con una acción YA EJECUTADA. Tu única tarea es convertir esos datos en UNA frase corta en español, sin añadir NINGÚN dato que no esté en el JSON.

Reglas estrictas:
- SOLO menciona título, fecha y hora si aparecen explícitamente en el JSON.
- NUNCA inventes que alguien "confirmó", "aceptó" o "respondió" nada -- no existe eso en este sistema.
- NUNCA cambies el significado de las palabras del título (si dice "comida", no lo llames "cena"; usa el título tal cual).
- Usa el tiempo verbal correcto: si "resultado" es "exito" y la acción es "crear", el evento AÚN NO HA OCURRIDO, así que no digas "has comido" o "te ha visto", di "vas a tener" o "queda agendado".
- Una sola frase, sin añadir despedidas ni comentarios de más.

Ejemplo 1:
{{"accion": "crear", "resultado": "exito", "titulo": "dentista", "fecha": "2026-08-26", "hora": "17:00"}}
Respuesta: Listo, tienes "dentista" agendado el 26 de agosto a las 17:00.

Ejemplo 2:
{{"accion": "eliminar", "resultado": "error", "motivo": "evento no encontrado", "titulo_buscado": "reunión"}}
Respuesta: No he encontrado ningún evento llamado "reunión".

Ejemplo 3:
{{"accion": "actualizar", "resultado": "exito", "titulo": "entreno", "nueva_fecha": "2026-08-27", "nueva_hora": "19:00"}}
Respuesta: Hecho, "entreno" queda movido al 27 de agosto a las 19:00.

Información:
{info}

Respuesta:
"""

def generate_response_text(info: dict, timeout: int = 10) -> str | None:
    prompt = RESPONSE_SYSTEM_PROMPT.format(info=json.dumps(info, ensure_ascii=False))

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    try:
        response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return None

    text = response.json().get("message", {}).get("content", "").strip()
    if not text:
        return None

    # Red de seguridad: si hay título en la info, debe aparecer literalmente
    # en la respuesta -- si no, sospechamos que el modelo alteró el contenido.
    titulo = info.get("titulo") or info.get("titulo_buscado")
    if titulo and titulo.lower() not in text.lower():
        return None

    return text