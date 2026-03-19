from google import genai
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.getcwd())
from src.lucidpanda.config import settings

def list_gemini_models():
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    print(f"Using API Key: {settings.GEMINI_API_KEY[:5]}...{settings.GEMINI_API_KEY[-5:] if settings.GEMINI_API_KEY else 'NONE'}")
    print("Listing available models...")
    try:
        # 尝试列出所有模型
        for i, m in enumerate(client.models.list()):
            print(f"- {m.name}")
            # 仅在第一个模型时打印出所有属性，以便我们调试
            if i == 0:
                print(f"  Available attributes: {[attr for attr in dir(m) if not attr.startswith('_')]}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_gemini_models()
