import speech_recognition as sr

def escuchar():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print(">>> Escuchando...")
        # Ajustamos para el ruido de fondo (importante para portátiles)
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=8)
            print(">>> Procesando...")
            text = r.recognize_google(audio, language="es-ES")
            return text
        except:
            return None
