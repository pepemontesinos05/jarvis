import ollama

class JarvisBrain:
    def __init__(self, model_name="llama3.2:1b"):
        self.model_name = model_name
        # Aquí guardamos la "personalidad"
        self.messages = [
            {
                'role': 'system', 
                'content': 'Eres Jarvis, el asistente de inteligencia artificial de Iron Man, pero ahora trabajas para tu creador en su PC. Eres culto, eficiente, un poco sarcástico pero extremadamente leal. Tus respuestas deben ser concisas y en español.'
            }
        ]

    def ask(self, question):
        # Añadimos la pregunta del usuario al historial
        self.messages.append({'role': 'user', 'content': question})
        
        try:
            response = ollama.chat(model=self.model_name, messages=self.messages)
            answer = response['message']['content']
            
            # Guardamos la respuesta para que tenga memoria de la conversación
            self.messages.append({'role': 'assistant', 'content': answer})
            return answer
        except Exception as e:
            return f"Señor, he tenido un error en mis circuitos: {e}"

# Prueba rápida para verificar que funciona
if __name__ == "__main__":
    brain = JarvisBrain()
    print(brain.ask("Jarvis, ¿estás en línea?"))
