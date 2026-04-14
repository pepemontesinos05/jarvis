import asyncio
from brain import JarvisBrain
from tts import speak
from stt import escuchar

async def main():
    jarvis = JarvisBrain()
    print("--- JARVIS: SISTEMA TOTALMENTE OPERATIVO ---")
    
    await speak("Sistemas en línea. Estoy escuchando, señor.")
    
    while True:
        # 1. Jarvis escucha
        comando = escuchar()
        
        if comando:
            print(f"Has dicho: {comando}")
            
            # Condición para apagarlo con la voz
            if any(p in comando.lower() for p in ["descansa", "adiós", "apágate"]):
                await speak("Entendido, señor. Desconectando sistemas de energía.")
                break
            
            # 2. Jarvis piensa
            respuesta = jarvis.ask(comando)
            print(f"Jarvis: {respuesta}")
            
            # 3. Jarvis habla
            await speak(respuesta)
        else:
            # Si no hay voz, el bucle sigue esperando
            continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSistemas interrumpidos.")
