import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)

try:
    print("Testing Gemini 3.5 Flash Lite...")

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents="Reply with: Gemini connection successful."
    )

    print("\nResponse:")
    print(response.text)

except errors.APIError as e:
    print("\nGemini API Error:")
    print(e)

finally:
    client.close()