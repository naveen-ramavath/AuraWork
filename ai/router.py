from ai.gemini_model import GeminiModel
from ai.groq_model import GroqModel


class AIRouter:

    def __init__(self):

        self.models = {
            "gemini": GeminiModel(),
            "groq": GroqModel(),
        }

    def generate(
        self,
        provider,
        user_message,
        tools,
        system_instruction,
    ):

        if provider not in self.models:
            raise ValueError(f"Unknown AI Provider: {provider}")

        return self.models[provider].generate(
            user_message,
            tools,
            system_instruction,
        )