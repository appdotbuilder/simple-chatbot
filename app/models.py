from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
from enum import Enum


class MessageType(str, Enum):
    """Type of message sender."""

    USER = "user"
    BOT = "bot"


# Persistent models (stored in database)
class User(SQLModel, table=True):
    """User model for chatbot application."""

    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100, unique=True)
    display_name: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    # Relationships
    conversations: List["Conversation"] = Relationship(back_populates="user")


class Conversation(SQLModel, table=True):
    """Conversation session model to group related messages."""

    __tablename__ = "conversations"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=500, default="New Conversation")
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    # Relationships
    user: User = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    """Individual message within a conversation."""

    __tablename__ = "messages"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(max_length=5000)
    message_type: MessageType = Field(default=MessageType.USER)
    conversation_id: int = Field(foreign_key="conversations.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional metadata for bot responses
    response_time_ms: Optional[int] = Field(default=None)
    model_used: Optional[str] = Field(default=None, max_length=100)

    # Relationships
    conversation: Conversation = Relationship(back_populates="messages")


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    """Schema for creating a new user."""

    username: str = Field(max_length=100)
    display_name: str = Field(max_length=200)


class UserUpdate(SQLModel, table=False):
    """Schema for updating user information."""

    display_name: Optional[str] = Field(default=None, max_length=200)
    is_active: Optional[bool] = Field(default=None)


class ConversationCreate(SQLModel, table=False):
    """Schema for creating a new conversation."""

    title: Optional[str] = Field(default="New Conversation", max_length=500)
    user_id: int


class ConversationUpdate(SQLModel, table=False):
    """Schema for updating conversation information."""

    title: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = Field(default=None)


class MessageCreate(SQLModel, table=False):
    """Schema for creating a new message."""

    content: str = Field(max_length=5000)
    message_type: MessageType = Field(default=MessageType.USER)
    conversation_id: int
    response_time_ms: Optional[int] = Field(default=None)
    model_used: Optional[str] = Field(default=None, max_length=100)


class MessageResponse(SQLModel, table=False):
    """Schema for message API responses."""

    id: int
    content: str
    message_type: MessageType
    conversation_id: int
    created_at: str  # ISO format datetime string
    response_time_ms: Optional[int] = None
    model_used: Optional[str] = None


class ConversationWithMessages(SQLModel, table=False):
    """Schema for conversation with its messages."""

    id: int
    title: str
    user_id: int
    created_at: str  # ISO format datetime string
    updated_at: str  # ISO format datetime string
    is_active: bool
    messages: List[MessageResponse]
