import os
import json
from dotenv import load_dotenv
from google import genai

from prompts.system_prompt import SYSTEM_PROMPT


# Cargar las variables de entorno
load_dotenv()


def main():
    print("=================================")
    print("      TUTOR TOGAF INICIADO")
    print("=================================")

    # Obtener la API Key
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("ERROR: No se encontró GEMINI_API_KEY.")
        print("Verifica que tengas configurado tu archivo .env")
        return

    # Crear el cliente de Gemini
    client = genai.Client(api_key=api_key)

    # Solicitar pregunta al usuario
    pregunta = input("\nEscribe tu pregunta sobre TOGAF: ")

    # Construir el prompt utilizando delimitadores XML
    prompt = f"""
<INSTRUCCIONES>
Utiliza el System Prompt proporcionado para responder la pregunta del estudiante.
</INSTRUCCIONES>

<CONTEXTO>
No se ha proporcionado contexto adicional.
</CONTEXTO>

<PREGUNTA>
{pregunta}
</PREGUNTA>
"""

    try:
        # Enviar la solicitud al modelo
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
            },
            contents=prompt,
        )

        # Obtener la respuesta
        respuesta = response.text

        print("\n=================================")
        print("        RESPUESTA DEL TUTOR")
        print("=================================")

        # Intentar interpretar la respuesta como JSON
        try:
            datos = json.loads(respuesta)
            print(json.dumps(datos, indent=4, ensure_ascii=False))
        except json.JSONDecodeError:
            print(respuesta)

    except Exception as e:
        print("\nERROR AL CONSULTAR EL MODELO:")
        print(e)


if __name__ == "__main__":
    main()