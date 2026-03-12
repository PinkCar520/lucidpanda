from google import genai
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.getcwd())
from src.alphasignal.config import settings

def list_gemini_models():
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    print("Listing models...")
    try:
        # Use v1 for listing if possible, or default
        for m in client.models.list():
            if 'embedContent' in m.supported_generation_methods or 'embed_content' in m.supported_generation_methods:
                print(f"Model Name: {m.name}, Display: {m.display_name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_gemini_models()
