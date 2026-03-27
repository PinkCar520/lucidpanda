import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-pro-latest"
]

for model_name in models_to_test:
    try:
        print(f"Testing {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'OK'"
        )
        print(f"✅ {model_name} is WORKING: {response.text.strip()}")
    except Exception as e:
        print(f"❌ {model_name} FAILED: {e}")
