import asyncio
import httpx
from openai import OpenAI
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
ai_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env.ai")
load_dotenv(env_path)
load_dotenv(ai_env_path, override=True)

from src.lucidpanda.config import settings

def test():
    client = OpenAI(
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL,
        http_client=httpx.Client(trust_env=False)
    )
    response = client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_tokens=2000
    )
    print("Response:")
    print(response.choices[0].message.content)

if __name__ == "__main__":
    test()
