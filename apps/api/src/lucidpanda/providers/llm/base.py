from abc import ABC, abstractmethod
from typing import Optional, Dict

class BaseLLM(ABC):
    @abstractmethod
    def analyze(self, raw_data: dict, taxonomy: Optional[Dict] = None):
        """同步分析核心接口"""
        pass

    @abstractmethod
    async def analyze_async(self, raw_data: dict, taxonomy: Optional[Dict] = None):
        """异步分析核心接口"""
        pass

    async def generate_json_async(self, prompt: str, temperature: float = 0.2):
        raise NotImplementedError("generate_json_async is not implemented for this provider")
