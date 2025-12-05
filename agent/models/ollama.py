from typing import Iterable
import os
from ollama import Client
from .base import BaseModelAdapter


class OllamaAdapter(BaseModelAdapter):
    def __init__(self, model_name: str, temperature: float = 0.7, max_new_tokens: int = 256):
        self.model_name = model_name
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        host = os.environ.get("OLLAMA_HOST")
        self.client = Client(host=host) if host else Client()

    def generate(self, prompt: str, stream: bool = False, **kwargs) -> Iterable[str]:
        options = {
            "temperature": self.temperature,
            "num_predict": self.max_new_tokens,
        }
        if stream:
            for chunk in self.client.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}], stream=True, options=options):
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
        else:
            resp = self.client.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}], stream=False, options=options)
            yield resp.get("message", {}).get("content", "")