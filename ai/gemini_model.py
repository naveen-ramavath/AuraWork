import json
import logging
import google.generativeai as genai
from ai.base import BaseAIModel

from config import Config
from ai.engine import AIEngine

logger = logging.getLogger(__name__)



class GeminiModel(BaseAIModel):
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)

    def generate(
        self,
        user_message: str,
        tools: list,
        system_instruction: str,
    ):

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=tools,
            system_instruction=system_instruction
        )

        chat = model.start_chat()

        response = chat.send_message(user_message)

        return AIEngine.execute(
            provider="gemini",
            chat=chat,
            response=response,
            tools=tools,
        )