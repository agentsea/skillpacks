from abc import ABC, abstractmethod

from PIL import Image

class OnlineCompletionModel(ABC):
    """LLM completion model with online fine tuning"""

    @abstractmethod
    def learn(self, prompt: str, image: str | Image.Image, response: str) -> float:
        pass

    @abstractmethod
    def complete(self, prompt: str, image: str | Image.Image) -> str:
        pass

    @abstractmethod
    def save(self, path: str = "./output") -> None:
        pass
    
    @abstractmethod
    def finish(self) -> None:
        pass