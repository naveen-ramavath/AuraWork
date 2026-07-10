from openai import OpenAI

from config import Config
from ai.base import BaseAIModel
from ai.engine import AIEngine


class DeepSeekModel(BaseAIModel):

    def __init__(self):

        self.client = OpenAI(
            base_url="https://api.deepseek.com",
            api_key=Config.DEEPSEEK_API_KEY
        )

    def generate(
        self,
        user_message,
        tools,
        system_instruction,
    ):

        return AIEngine.execute(
            provider="deepseek",
            client=self.client,
            user_message=user_message,
            tools=tools,
            system_instruction=system_instruction,
        )
