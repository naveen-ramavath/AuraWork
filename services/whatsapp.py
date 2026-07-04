# from IPython.core import application
# from IPython.core import application
# from IPython.core import application
# from urllib import response
import logging
import requests
from config import Config

logger = logging.getLogger(__name__)

def get_whatsapp_headers():
    """Generates Authorization headers for the WhatsApp Cloud API."""
    return {
        "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

def send_text(to: str, body: str) -> bool:
    if not Config.WHATSAPP_TOKEN or not Config.PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not set.")
        return False

    url = f"https://graph.facebook.com/{Config.API_VERSION}/{Config.PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": body
        }
    }

    try:
        print("=" * 60)
        print("URL:", url)
        print("HEADERS:", get_whatsapp_headers())
        print("PAYLOAD:", payload)
        print("=" * 60)
        response = requests.post(
            url,
            json=payload,
            headers=get_whatsapp_headers(),
            timeout=10
        )

        print("=" * 70)
        print("STATUS :", response.status_code)
        print("BODY   :", response.text)
        print("=" * 70)

        if response.ok:
            logger.info(f"Message sent to {to}")
            return True

        logger.error(f"WhatsApp API Error: {response.text}")
        return False

    except Exception:
        logger.exception("Exception while sending WhatsApp message")
        return False

def mark_read(message_id: str) -> bool:
    """Marks an incoming WhatsApp message as read to acknowledge receipt."""
    if not Config.WHATSAPP_TOKEN or not Config.PHONE_NUMBER_ID:
        return False

    url = f"https://graph.facebook.com/{Config.API_VERSION}/{Config.PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }
    
    try:
        response = requests.post(url, json=payload, headers=get_whatsapp_headers(), timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.exception(f"Exception marking message {message_id} as read: {e}")
        return False

def send_media(to: str, media_id: str, media_type: str = "image") -> bool:
    """Sends uploaded media (image, video, document) to a user via ID."""
    if not Config.WHATSAPP_TOKEN or not Config.PHONE_NUMBER_ID:
        return False

    url = f"https://graph.facebook.com/{Config.API_VERSION}/{Config.PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": media_type,
        media_type: {"id": media_id}
    }
    
    try:
        response = requests.post(url, json=payload, headers=get_whatsapp_headers(), timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.exception(f"Exception sending {media_type} to {to}: {e}")
        return False
