import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL")

class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def generate(self, messages, **params):
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": MODEL,
            "messages": messages,
            **params,
        }

        response = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter error: {response.text}")

        return response.json()