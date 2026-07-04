import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import Config

logger = logging.getLogger(__name__)

def get_slack_client(token: str = None) -> WebClient:
    """Returns a Slack WebClient initialized with the provided user token or the default bot token."""
    slack_token = token or Config.SLACK_BOT_TOKEN
    return WebClient(token=slack_token)

def post_message_to_slack(channel: str, text: str, token: str = None) -> bool:
    """Posts a message to a specific Slack channel or user DM."""
    client = get_slack_client(token)
    try:
        response = client.chat_postMessage(channel=channel, text=text)
        return response["ok"]
    except SlackApiError as e:
        logger.error(f"Slack API error posting message: {e.response['error']}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error posting to Slack: {e}")
        return False

def get_slack_unread_mentions(token: str = None) -> list:
    """Fetches recent mentions or unread notifications for the user."""
    client = get_slack_client(token)
    try:
        # Fetching channels history or search results to locate user mentions.
        # For simplicity in this demo/reference, we call users.conversations to get DM list
        # or search for messages containing the user ID.
        # Real-world apps query the slack events API, or search messages matching the authenticated user.
        auth_test = client.auth_test()
        user_id = auth_test.get("user_id")
        
        # Simple search query for mentions of the active user
        if user_id:
            search_query = f"<@{user_id}>"
            result = client.search_messages(query=search_query, count=5)
            mentions = []
            if result.get("ok"):
                for match in result.get("messages", {}).get("matches", []):
                    mentions.append({
                        "channel": match.get("channel", {}).get("name", "unknown"),
                        "username": match.get("username"),
                        "text": match.get("text"),
                        "permalink": match.get("permalink")
                    })
                return mentions
        return []
    except SlackApiError as e:
        logger.error(f"Slack API error fetching mentions: {e.response['error']}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error fetching Slack mentions: {e}")
        return []
