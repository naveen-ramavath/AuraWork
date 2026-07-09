import json
import logging
import google.generativeai as genai

from config import Config

logger = logging.getLogger(__name__)


class GeminiModel:

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

        loop_limit = 5

        for _ in range(loop_limit):

            function_calls = []

            if response.candidates and response.candidates[0].content:

                for part in response.candidates[0].content.parts:

                    if part.function_call and part.function_call.name:
                        function_calls.append(part.function_call)

            if not function_calls:
                break

            tool_responses = []

            for call in function_calls:

                tool_name = call.name
                tool_args = dict(call.args)

                logger.info(
                    f"Model requested tool: {tool_name} with args: {tool_args}"
                )

                try:
                    tool_func = next(
                        t for t in tools
                        if t.__name__ == tool_name
                    )

                    result = tool_func(**tool_args)

                except Exception as err:

                    logger.exception(err)

                    result = json.dumps({
                        "status": "error",
                        "message": str(err)
                    })

                tool_responses.append({
                    "function_response": {
                        "name": tool_name,
                        "response": {
                            "result": result
                        }
                    }
                })

            response = chat.send_message(tool_responses)

        return response.text