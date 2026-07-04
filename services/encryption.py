import os
import logging
from cryptography.fernet import Fernet
from config import Config

logger = logging.getLogger(__name__)

# Fallback development key (ensure to configure ENCRYPTION_KEY in production)
DEV_KEY = b'U3luY0NvcGlsb3REZXZFbmNyeXB0aW9uS2V5MTIzNDU2Nzg='

def get_fernet_key() -> bytes:
    """Retrieves the encryption key from the environment configuration."""
    key_str = os.getenv("ENCRYPTION_KEY")
    if not key_str:
        logger.warning("ENCRYPTION_KEY not set in .env. Using fallback development key.")
        return DEV_KEY
    try:
        return key_str.encode()
    except Exception as e:
        logger.error(f"Invalid ENCRYPTION_KEY format. Error: {e}. Using fallback key.")
        return DEV_KEY

def encrypt_data(plain_text: str) -> str:
    """Encrypts a string value using Fernet (AES-128)."""
    if not plain_text:
        return ""
    try:
        f = Fernet(get_fernet_key())
        return f.encrypt(plain_text.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return ""

def decrypt_data(cipher_text: str) -> str:
    """Decrypts a Fernet encrypted string back to plaintext."""
    if not cipher_text:
        return ""
    try:
        f = Fernet(get_fernet_key())
        return f.decrypt(cipher_text.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ""
