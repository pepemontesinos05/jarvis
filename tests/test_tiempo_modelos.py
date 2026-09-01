# tests/test_stt_timing.py

import time
from services.audio.stt import _get_model, record_audio, transcribe

print("Cargando modelo (esto puede tardar la primera vez)...")
t0 = time.time()
_get_model()
print(f"Modelo cargado en {time.time() - t0:.2f}s (esto solo pasa una vez por sesión)")

print("\nHabla ahora...")
audio = record_audio()

t0 = time.time()
texto = transcribe(audio)
print(f"Transcripción ({time.time() - t0:.2f}s): {texto}")

print("\nSegunda prueba, para ver la latencia real de uso repetido...")
input("Pulsa Enter y habla de nuevo...")
audio2 = record_audio()

t0 = time.time()
texto2 = transcribe(audio2)
print(f"Transcripción ({time.time() - t0:.2f}s): {texto2}")