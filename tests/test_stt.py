# tests/test_stt.py

print("Antes de grabar...")
from services.audio.stt import record_audio, transcribe

print("Habla ahora (5 segundos para empezar, 8 segundos de frase máximo)...")
audio = record_audio()
print("Después de grabar, audio =", audio)  # <- si esto no se imprime nunca, el problema es record_audio()

if audio is None:
    print("No se detectó voz a tiempo.")
else:
    print("Antes de transcribir...")
    texto = transcribe(audio)
    print(f"Transcripción: {texto}")