from typing import Iterable
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from .base import BaseModelAdapter


class HFAdapter(BaseModelAdapter):
    def __init__(self, model_name: str, device: str = "cpu", temperature: float = 0.7, max_new_tokens: int = 256):
        self.model_name = model_name
        self.device = device
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32)
        self.model.to(self.device)

    def generate(self, prompt: str, stream: bool = False, **kwargs) -> Iterable[str]:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                do_sample=True,
                temperature=self.temperature,
                max_new_tokens=self.max_new_tokens,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        # 简单地从原始输入后截取新生成的部分
        if text.startswith(prompt):
            yield text[len(prompt):]
        else:
            yield text