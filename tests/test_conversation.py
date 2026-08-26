# tests/test_conversation.py

from skills.calendar.skill import CalendarSkill

skill = CalendarSkill()

print("--- JARVIS V0 (texto) ---")
print("Escribe una orden de calendario, o 'salir' para terminar.\n")

while True:
    orden = input("Tú: ").strip()

    if orden.lower() in ("salir", "exit", "adiós"):
        print("Jarvis: Hasta luego.")
        break

    if not orden:
        continue

    resultado = skill.execute({"raw_text": orden})

    estado = "✅" if resultado.success else "❌"
    print(f"Jarvis {estado}: {resultado.message}")
    if resultado.data:
        print(f"   (data: {resultado.data})")
    print()