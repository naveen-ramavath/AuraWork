import logging
from ai.gemini_model import GeminiModel
from ai.groq_model import GroqModel

logger = logging.getLogger(__name__)


class MessageClassifier:
    """
    Classifies user messages to determine the optimal AI provider.
    """

    @staticmethod
    def classify(message: str) -> str:
        """
        Classifies a user message to decide the best model provider:
        - "groq" for general conversation, greetings, casual questions.
        - "gemini" for email, calendar, slack, jira, reasoning, and long planning.
        """
        msg = message.lower().strip()

        # Obvious greetings/casual questions/courtesies
        greetings = {
            "hi", "hello", "hey", "yo", "greetings", "hola",
            "good morning", "good afternoon", "good evening",
            "how are you", "how's it going", "howdy",
            "thank you", "thanks", "thanks a lot", "thank you very much",
            "bye", "goodbye", "see you", "who are you", "what are you",
            "what is your name", "what's your name", "tell me a joke"
        }

        # Check if message contains tool keywords to override greetings
        tool_keywords = [
            "email", "mail", "gmail", "calendar", "meeting", "schedule",
            "event", "slack", "jira", "ticket", "log work"
        ]
        has_tool_keywords = any(kw in msg for kw in tool_keywords)

        if has_tool_keywords:
            return "gemini"

        # Check if matches any greeting
        is_greeting = (
            msg in greetings or 
            any(msg.startswith(g) for g in greetings) or 
            any(msg.endswith(g) for g in greetings)
        )

        if is_greeting:
            return "groq"

        # Short general conversational phrases
        if len(msg.split()) <= 3:
            return "groq"

        # Default to Gemini for complex task execution, planning, and reasoning
        return "gemini"


class AIRouter:

    def __init__(self):

        self.models = {
            "gemini": GeminiModel(),
            "groq": GroqModel(),
        }
        self.classifier = MessageClassifier()

    def generate(
        self,
        provider,
        user_message,
        tools,
        system_instruction,
    ):

        # If provider is "auto" or "gemini" (default configuration), we use the Smart Router
        # to automatically classify the message. If provider is explicitly "groq", we respect it.
        if provider in ("auto", "gemini") or not provider:
            chosen_provider = self.classifier.classify(user_message)
        else:
            chosen_provider = provider

        logger.info(
            f"Smart Routing classified message: '{user_message[:50]}...' -> Selected Provider: '{chosen_provider}' (requested: '{provider}')"
        )

        if chosen_provider not in self.models:
            raise ValueError(f"Unknown AI Provider: {chosen_provider}")

        # Execute with fallback logic
        if chosen_provider == "gemini":
            try:
                logger.info("Attempting generation using Gemini...")
                return self.models["gemini"].generate(
                    user_message,
                    tools,
                    system_instruction,
                )
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}. Falling back to Groq...")
                try:
                    return self.models["groq"].generate(
                        user_message,
                        tools,
                        system_instruction,
                    )
                except Exception as groq_err:
                    logger.error(f"Groq fallback also failed: {groq_err}")
                    raise groq_err
        else:
            try:
                logger.info("Attempting generation using Groq...")
                return self.models["groq"].generate(
                    user_message,
                    tools,
                    system_instruction,
                )
            except Exception as e:
                logger.warning(f"Groq generation failed: {e}. Falling back to Gemini...")
                try:
                    return self.models["gemini"].generate(
                        user_message,
                        tools,
                        system_instruction,
                    )
                except Exception as gemini_err:
                    logger.error(f"Gemini fallback also failed: {gemini_err}")
                    raise gemini_err