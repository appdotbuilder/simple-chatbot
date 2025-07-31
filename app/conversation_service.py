"""
Conversation service module for managing users, conversations, and messages.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import select, desc, asc
from app.models import (
    User,
    UserCreate,
    Conversation,
    ConversationCreate,
    Message,
    MessageCreate,
    MessageResponse,
    ConversationWithMessages,
    MessageType,
)
from app.database import get_session
from logging import getLogger

logger = getLogger(__name__)


class ConversationService:
    """Service for managing conversations, users, and messages."""

    def get_or_create_user(self, username: str, display_name: Optional[str] = None) -> Optional[User]:
        """Get existing user or create a new one."""
        try:
            with get_session() as session:
                # Try to find existing user
                statement = select(User).where(User.username == username)
                user = session.exec(statement).first()

                if user:
                    return user

                # Create new user
                user_data = UserCreate(username=username, display_name=display_name or username)
                user = User(**user_data.model_dump())
                session.add(user)
                session.commit()
                session.refresh(user)

                logger.info(f"Created new user: {username}")
                return user

        except Exception as e:
            logger.error(f"Failed to get or create user {username}: {e}")
            return None

    def create_conversation(self, user_id: int, title: Optional[str] = None) -> Optional[Conversation]:
        """Create a new conversation for a user."""
        try:
            with get_session() as session:
                conversation_data = ConversationCreate(user_id=user_id, title=title or "New Conversation")
                conversation = Conversation(**conversation_data.model_dump())
                session.add(conversation)
                session.commit()
                session.refresh(conversation)

                logger.info(f"Created new conversation {conversation.id} for user {user_id}")
                return conversation

        except Exception as e:
            logger.error(f"Failed to create conversation for user {user_id}: {e}")
            return None

    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID."""
        try:
            with get_session() as session:
                return session.get(Conversation, conversation_id)
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None

    def get_user_conversations(self, user_id: int, active_only: bool = True) -> List[Conversation]:
        """Get all conversations for a user."""
        try:
            with get_session() as session:
                statement = select(Conversation).where(Conversation.user_id == user_id)
                if active_only:
                    statement = statement.where(Conversation.is_active)
                statement = statement.order_by(desc(Conversation.updated_at))

                conversations = session.exec(statement).all()
                return list(conversations)

        except Exception as e:
            logger.error(f"Failed to get conversations for user {user_id}: {e}")
            return []

    def create_message(
        self,
        content: str,
        message_type: MessageType,
        conversation_id: int,
        response_time_ms: Optional[int] = None,
        model_used: Optional[str] = None,
    ) -> Optional[Message]:
        """Create and save a new message."""
        try:
            with get_session() as session:
                message_data = MessageCreate(
                    content=content,
                    message_type=message_type,
                    conversation_id=conversation_id,
                    response_time_ms=response_time_ms,
                    model_used=model_used,
                )
                message = Message(**message_data.model_dump())
                session.add(message)
                session.commit()
                session.refresh(message)

                # Update conversation's updated_at timestamp
                conversation = session.get(Conversation, conversation_id)
                if conversation:
                    conversation.updated_at = datetime.utcnow()
                    session.add(conversation)
                    session.commit()

                # Create a new instance to avoid detached session issues
                message_dict = {
                    "id": message.id,
                    "content": message.content,
                    "message_type": message.message_type,
                    "conversation_id": message.conversation_id,
                    "created_at": message.created_at,
                    "response_time_ms": message.response_time_ms,
                    "model_used": message.model_used,
                }
                return Message(**message_dict)

        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            return None

    def get_conversation_messages(self, conversation_id: int, limit: Optional[int] = None) -> List[Message]:
        """Get all messages for a conversation."""
        try:
            with get_session() as session:
                statement = select(Message).where(Message.conversation_id == conversation_id)
                statement = statement.order_by(asc(Message.created_at))

                if limit:
                    statement = statement.limit(limit)

                messages = session.exec(statement).all()
                return list(messages)

        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            return []

    def get_conversation_with_messages(self, conversation_id: int) -> Optional[ConversationWithMessages]:
        """Get a conversation with all its messages."""
        try:
            with get_session() as session:
                conversation = session.get(Conversation, conversation_id)
                if not conversation:
                    return None

                messages = self.get_conversation_messages(conversation_id)

                # Convert messages to response format
                message_responses = [
                    MessageResponse(
                        id=msg.id or 0,
                        content=msg.content,
                        message_type=msg.message_type,
                        conversation_id=msg.conversation_id,
                        created_at=msg.created_at.isoformat(),
                        response_time_ms=msg.response_time_ms,
                        model_used=msg.model_used,
                    )
                    for msg in messages
                ]

                return ConversationWithMessages(
                    id=conversation.id or 0,
                    title=conversation.title,
                    user_id=conversation.user_id,
                    created_at=conversation.created_at.isoformat(),
                    updated_at=conversation.updated_at.isoformat(),
                    is_active=conversation.is_active,
                    messages=message_responses,
                )

        except Exception as e:
            logger.error(f"Failed to get conversation with messages {conversation_id}: {e}")
            return None

    def update_conversation_title(self, conversation_id: int, title: str) -> Optional[Conversation]:
        """Update a conversation's title."""
        try:
            with get_session() as session:
                conversation = session.get(Conversation, conversation_id)
                if not conversation:
                    return None

                conversation.title = title
                conversation.updated_at = datetime.utcnow()
                session.add(conversation)
                session.commit()
                session.refresh(conversation)

                return conversation

        except Exception as e:
            logger.error(f"Failed to update conversation title {conversation_id}: {e}")
            return None

    def delete_conversation(self, conversation_id: int) -> bool:
        """Mark a conversation as inactive (soft delete)."""
        try:
            with get_session() as session:
                conversation = session.get(Conversation, conversation_id)
                if not conversation:
                    return False

                conversation.is_active = False
                conversation.updated_at = datetime.utcnow()
                session.add(conversation)
                session.commit()

                logger.info(f"Marked conversation {conversation_id} as inactive")
                return True

        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False


# Global conversation service instance
conversation_service = ConversationService()
