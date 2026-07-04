from google import auth
import datetime
import json
import logging
# pyrefly: ignore [missing-import]
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
# from sqlalchemy.orm import Session

from config import Config
from database.models import User, UserAuth
from database.postgres import SessionLocal
from services.encryption import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

# Scopes needed for Gmail (reading, drafting) and Calendar (viewing, managing events)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar"
]

def get_client_config() -> dict:
    """Formats Google Client Config from settings."""
    return {
        "web": {
            "client_id": Config.GOOGLE_CLIENT_ID,
            "client_secret": Config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [Config.GOOGLE_REDIRECT_URI]
        }
    }

def get_google_auth_url(phone_number: str) -> str:
    """Generates Google Sign-In authorization URL, passing phone number in state."""
    client_config = get_client_config()
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=Config.GOOGLE_REDIRECT_URI
    )
    
    # State parameter passes the user phone number back to the callback
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=phone_number,
        prompt="consent"
    )
    return authorization_url

def handle_oauth_callback(code: str, state_phone: str) -> bool:
    """Exchanges auth code for tokens and saves/updates them in the database with encryption."""
    db = SessionLocal()
    try:
        client_config = get_client_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=Config.GOOGLE_REDIRECT_URI
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Check if user exists, else create
        user = db.query(User).filter(User.phone_number == state_phone).first()
        if not user:
            user = User(phone_number=state_phone)
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # Check if user auth exists, else create
        auth = db.query(UserAuth).filter(UserAuth.user_id == user.id).first()
        if not auth:
            auth = UserAuth(user_id=user.id)
            db.add(auth)
            
        # Encrypt before saving to database
        auth.google_access_token = encrypt_data(credentials.token)
        if credentials.refresh_token:
            auth.google_refresh_token = encrypt_data(credentials.refresh_token)
        auth.google_token_expiry = credentials.expiry
        
        db.commit()
        logger.info(f"Successfully saved Google OAuth credentials (encrypted) for user {state_phone}")
        return True
    except Exception as e:
        logger.exception(f"Error handling Google OAuth callback: {e}")
        return False
    finally:
        db.close()

def get_user_credentials(phone_number: str):
    db = SessionLocal()

    try:
        print("=" * 60)
        print("PHONE:", phone_number)

        user = db.query(User).filter(User.phone_number == phone_number).first()

        print("USER:", user)

        if not user:
            print("USER NOT FOUND")
            return None

        print("USER ID:", user.id)
        print("AUTH:", user.auth)

        if not user.auth:
            print("NO AUTH OBJECT")
            return None

        auth = user.auth

        print("ACCESS TOKEN EXISTS:", bool(auth.google_access_token))
        print("REFRESH TOKEN EXISTS:", bool(auth.google_refresh_token))

        access = decrypt_data(auth.google_access_token)
        refresh = decrypt_data(auth.google_refresh_token)

        print("DECRYPTED ACCESS:", access[:20] if access else None)
        print("DECRYPTED REFRESH:", refresh[:20] if refresh else None)

        creds = Credentials(
            token=access,
            refresh_token=refresh,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )

        if auth.google_token_expiry:
            creds.expiry = auth.google_token_expiry

        print("Expired:", creds.expired)

        if creds.expired:
            print("Refreshing token...")
            creds.refresh(Request())
            print("Refresh successful")

        print("Returning credentials")
        return creds

    except Exception as e:
        logger.exception(e)
        return None

    finally:
        db.close()
