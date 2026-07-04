import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.postgres import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    timezone = Column(String, default="Asia/Kolkata")  # Default to India local time or UTC
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    auth = relationship("UserAuth", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserAuth(Base):
    __tablename__ = "user_auths"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Google (Gmail & Calendar) Tokens
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_token_expiry = Column(DateTime, nullable=True)

    # Slack Credentials
    slack_user_token = Column(Text, nullable=True)

    # Jira Credentials
    jira_api_token = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="auth")

class SessionState(Base):
    __tablename__ = "session_states"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    state = Column(String, default="idle")  # e.g., 'idle', 'awaiting_standup', 'awaiting_email_recipient', etc.
    context_data = Column(Text, nullable=True)  # JSON-encoded metadata dictionary
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
