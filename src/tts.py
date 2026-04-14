import edge_tts
import asyncio
import pygame
import os

async def speak(text):
    # Definimos la voz (Alvaro es muy natural para un asistente)
    VOICE = "es-ES-AlvaroNeural"
    OUTPUT_FILE = "tmp_voice.mp3"

    # 1. Generar el archivo de audio con la IA de Microsoft
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(OUTPUT_FILE)

    # 2. Reproducir el audio
    pygame.mixer.init()
    pygame.mixer.music.load(OUTPUT_FILE)
    pygame.mixer.music.play()

    # Esperamos a que termine de hablar antes de seguir
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

    pygame.mixer.quit()
    
    # 3. Limpieza: eliminamos el archivo temporal
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
