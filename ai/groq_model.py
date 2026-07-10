from groq import Groq

from config import Config
from ai.base import BaseAIModel
from ai.engine import AIEngine


class GroqModel(BaseAIModel):

    def __init__(self):

        self.client = Groq(
            api_key=Config.GROQ_API_KEY
        )

    def generate(
        self,
        user_message,
        tools,
        system_instruction,
    ):

        return AIEngine.execute(
            provider="groq",
            client=self.client,
            user_message=user_message,
            tools=tools,
            system_instruction=system_instruction,
        )