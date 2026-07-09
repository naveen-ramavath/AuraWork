from abc import ABC, abstractmethod


class BaseAIModel(ABC):

    @abstractmethod
    def generate(self, user_message: str) -> str:
        pass