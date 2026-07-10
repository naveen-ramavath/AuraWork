import logging
from ai.gemini_model import GeminiModel
from ai.groq_model import GroqModel
from ai.openrouter_model import OpenRouterModel
from ai.deepseek_model import DeepSeekModel

logger = logging.getLogger(__name__)


class RoutingRule:
    """
    Encapsulates a message routing rule mapping keywords to a specific AI provider.
    """

    def __init__(self, provider: str, keywords: list, name: str):
        self.provider = provider
        self.keywords = [kw.lower() for kw in keywords]
        self.name = name

    def matches(self, message: str) -> bool:
        msg = message.lower()
        return any(kw in msg for kw in self.keywords)


class MessageClassifier:
    """
    Object-oriented rule-based classifier that maps user messages to AI providers.
    """

    def __init__(self):
        self.rules = [
            # 1. Tool Integrations (Email, Calendar, Slack, Jira) -> Gemini
            RoutingRule(
                provider="gemini",
                keywords=[
                    "email", "mail", "gmail", "calendar", "meeting", "schedule",
                    "event", "slack", "jira", "ticket", "worklog", "log work"
                ],
                name="Tool Integrations"
            ),
            # 2. Programming / Coding -> DeepSeek
            RoutingRule(
                provider="deepseek",
                keywords=[
                    "code", "program", "python", "javascript", "html", "css",
                    "function", "class", "write a script", "debug", "compile",
                    "syntax", "database", "sql"
                ],
                name="Programming"
            ),
            # 3. Creative writing -> OpenRouter
            RoutingRule(
                provider="openrouter",
                keywords=[
                    "write a story", "creative", "poem", "essay", "draft",
                    "creative writing", "novel", "fiction", "write a paragraph about"
                ],
                name="Creative Writing"
            ),
            # 4. Long Reasoning -> Gemini
            RoutingRule(
                provider="gemini",
                keywords=[
                    "reasoning", "planning", "explain step by step", "think carefully",
                    "reason"
                ],
                name="Long Reasoning"
            ),
            # 5. Greetings and General Conversation -> Groq
            RoutingRule(
                provider="groq",
                keywords=[
                    "hi", "hello", "hey", "yo", "greetings", "hola",
                    "good morning", "good afternoon", "good evening",
                    "how are you", "how's it going", "howdy",
                    "thank you", "thanks", "thanks a lot", "thank you very much",
                    "bye", "goodbye", "see you", "who are you", "what are you",
                    "what is your name", "what's your name", "tell me a joke"
                ],
                name="Greetings & General Conversation"
            ),
        ]
        self.default_provider = "gemini"

    def classify(self, message: str) -> str:
        msg = message.lower().strip()

        # Check each rule sequentially
        for rule in self.rules:
            if rule.matches(msg):
                logger.info(f"Message matched routing rule: '{rule.name}' -> Selected Provider: '{rule.provider}'")
                return rule.provider

        # General short greetings or casual conversational replies default to Groq
        if len(msg.split()) <= 3:
            return "groq"

        return self.default_provider


class AIRouter:

    def __init__(self):

        self.models = {
            "gemini": GeminiModel(),
            "groq": GroqModel(),
            "openrouter": OpenRouterModel(),
            "deepseek": DeepSeekModel(),
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
        # to automatically classify the message. If provider is explicitly set, we respect it.
        if provider in ("auto", "gemini") or not provider:
            chosen_provider = self.classifier.classify(user_message)
        else:
            chosen_provider = provider

        logger.info(
            f"Smart Routing classified message: '{user_message[:50]}...' -> Selected Provider: '{chosen_provider}' (requested: '{provider}')"
        )

        if chosen_provider not in self.models:
            raise ValueError(f"Unknown AI Provider: {chosen_provider}")

        # Setup prioritized fallback order based on the exact sequence: Gemini -> Groq -> OpenRouter -> DeepSeek
        fallback_sequence = ["gemini", "groq", "openrouter", "deepseek"]

        try:
            start_index = fallback_sequence.index(chosen_provider)
        except ValueError:
            start_index = 0

        providers_to_try = fallback_sequence[start_index:]

        last_exception = None
        for p in providers_to_try:
            try:
                logger.info(f"Attempting generation using {p}...")
                result = self.models[p].generate(
                    user_message,
                    tools,
                    system_instruction,
                )
                logger.info(f"Successfully generated response using provider: '{p}'")
                return result
            except Exception as e:
                logger.warning(f"{p} generation failed: {e}. Trying next fallback...")
                last_exception = e

        logger.error("All AI providers in the fallback chain failed.")
        if last_exception:
            raise last_exception
        raise RuntimeError("No AI model succeeded in generating a response.")