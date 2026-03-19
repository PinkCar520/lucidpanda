from abc import ABC, abstractmethod

class BaseLLM(ABC):
    @abstractmethod
    def analyze(self, text):
        pass

    async def generate_json_async(self, prompt: str, temperature: float = 0.2):
        raise NotImplementedError("generate_json_async is not implemented for this provider")
