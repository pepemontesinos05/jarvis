# tests/test_stt_debug.py

from services.audio.stt import record_audio, transcribe

print("Habla ahora...")
audio = record_audio()

if audio:
    with open("/tmp/audio_capturado.wav", "wb") as f:
        f.write(audio.get_wav_data())
    print("Audio guardado en /tmp/audio_capturado.wav")

    texto = transcribe(audio)
    print(f"Transcripción: {texto}")