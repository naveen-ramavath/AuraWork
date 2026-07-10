from openai import OpenAI

from config import Config
from ai.base import BaseAIModel
from ai.engine import AIEngine


class OpenRouterModel(BaseAIModel):

    def __init__(self):

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=Config.OPENROUTER_API_KEY
        )

    def generate(
        self,
        user_message,
        tools,
        system_instruction,
    ):

        return AIEngine.execute(
            provider="openrouter",
            client=self.client,
            user_message=user_message,
            tools=tools,
            system_instruction=system_instruction,
        )
