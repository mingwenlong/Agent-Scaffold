from typing import Iterable


class BaseModelAdapter:
    def generate(self, prompt: str, stream: bool = False, **kwargs) -> Iterable[str]:
        raise NotImplementedError