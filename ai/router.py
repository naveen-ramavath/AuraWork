from ai.gemini_model import GeminiModel


class AIRouter:

    def __init__(self):
        self.gemini = GeminiModel()

    def generate(
        self,
        user_message,
        tools,
        system_instruction
    ):

        return self.gemini.generate(
            user_message,
            tools,
            system_instruction
        )