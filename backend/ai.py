import os
from dotenv import load_dotenv
from google import genai

load_dotenv()



client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


def ask_gemini(message:str):
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents = message
    )

    return response.text