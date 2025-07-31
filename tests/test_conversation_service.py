"""
Tests for conversation service functionality.
"""

import pytest
from app.conversation_service import ConversationService, conversation_service
from app.models import MessageType
from app.database import reset_db
from datetime import datetime


@pytest.fixture()
def new_db():
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def sample_user(new_db):
    """Create a test user."""
    user = conversation_service.get_or_create_user("test_user", "Test User")
    assert user is not None
    return user


@pytest.fixture()
def sample_conversation(sample_user):
    """Create a test conversation."""
    assert sample_user.id is not None
    conversation = conversation_service.create_conversation(sample_user.id, "Test Chat")
    assert conversation is not None
    return conversation


class TestConversationService:
    """Test conversation service functionality."""

    def test_service_initialization(self):
        """Test service initializes correctly."""
        service = ConversationService()
        assert isinstance(service, ConversationService)

    def test_get_or_create_user_new(self, new_db):
        """Test creating a new user."""
        service = ConversationService()

        user = service.get_or_create_user("new_user", "New User")

        assert user is not None
        assert user.id is not None
        assert user.username == "new_user"
        assert user.display_name == "New User"
        assert user.is_active
        assert isinstance(user.created_at, datetime)

    def test_get_or_create_user_existing(self, sample_user):
        """Test getting an existing user."""
        service = ConversationService()

        # Get the same user
        user = service.get_or_create_user("test_user", "Different Name")

        assert user is not None
        assert user.id == sample_user.id
        assert user.username == "test_user"
        assert user.display_name == "Test User"  # Should keep original display name

    def test_get_or_create_user_default_display_name(self, new_db):
        """Test creating user with default display name."""
        service = ConversationService()

        user = service.get_or_create_user("simple_user")

        assert user is not None
        assert user.username == "simple_user"
        assert user.display_name == "simple_user"  # Should default to username

    def test_create_conversation(self, sample_user):
        """Test conversation creation."""
        service = ConversationService()
        assert sample_user.id is not None

        conversation = service.create_conversation(sample_user.id, "My Chat")

        assert conversation is not None
        assert conversation.id is not None
        assert conversation.title == "My Chat"
        assert conversation.user_id == sample_user.id
        assert conversation.is_active
        assert isinstance(conversation.created_at, datetime)
        assert isinstance(conversation.updated_at, datetime)

    def test_create_conversation_default_title(self, sample_user):
        """Test conversation creation with default title."""
        service = ConversationService()
        assert sample_user.id is not None

        conversation = service.create_conversation(sample_user.id)

        assert conversation is not None
        assert conversation.title == "New Conversation"

    def test_create_conversation_invalid_user(self, new_db):
        """Test conversation creation with invalid user ID."""
        service = ConversationService()

        conversation = service.create_conversation(99999, "Test")

        assert conversation is None

    def test_get_conversation(self, sample_conversation):
        """Test getting conversation by ID."""
        service = ConversationService()

        conversation = service.get_conversation(sample_conversation.id)

        assert conversation is not None
        assert conversation.id == sample_conversation.id
        assert conversation.title == sample_conversation.title

    def test_get_conversation_not_found(self, new_db):
        """Test getting non-existent conversation."""
        service = ConversationService()

        conversation = service.get_conversation(99999)

        assert conversation is None

    def test_get_user_conversations(self, sample_user):
        """Test getting user's conversations."""
        service = ConversationService()
        assert sample_user.id is not None

        # Create multiple conversations
        conv1 = service.create_conversation(sample_user.id, "First Chat")
        conv2 = service.create_conversation(sample_user.id, "Second Chat")
        assert conv1 is not None and conv2 is not None

        conversations = service.get_user_conversations(sample_user.id)

        assert len(conversations) == 2
        # Should be ordered by updated_at desc (newest first)
        assert conversations[0].id == conv2.id  # Second chat is newer
        assert conversations[1].id == conv1.id

    def test_get_user_conversations_active_only(self, sample_user):
        """Test getting only active conversations."""
        service = ConversationService()
        assert sample_user.id is not None

        # Create conversations
        conv1 = service.create_conversation(sample_user.id, "Active Chat")
        conv2 = service.create_conversation(sample_user.id, "Inactive Chat")
        assert conv1 is not None and conv2 is not None

        # Mark one as inactive
        assert conv2.id is not None
        success = service.delete_conversation(conv2.id)
        assert success

        # Get active conversations only
        conversations = service.get_user_conversations(sample_user.id, active_only=True)

        assert len(conversations) == 1
        assert conversations[0].id == conv1.id

        # Get all conversations
        all_conversations = service.get_user_conversations(sample_user.id, active_only=False)
        assert len(all_conversations) == 2

    def test_get_user_conversations_empty(self, sample_user):
        """Test getting conversations for user with none."""
        service = ConversationService()
        assert sample_user.id is not None

        conversations = service.get_user_conversations(sample_user.id)

        assert conversations == []

    def test_create_message(self, sample_conversation):
        """Test message creation."""
        service = ConversationService()

        message = service.create_message(
            content="Hello world!", message_type=MessageType.USER, conversation_id=sample_conversation.id
        )

        assert message is not None
        assert message.id is not None
        assert message.content == "Hello world!"
        assert message.message_type == MessageType.USER
        assert message.conversation_id == sample_conversation.id
        assert isinstance(message.created_at, datetime)

    def test_create_message_with_metadata(self, sample_conversation):
        """Test message creation with bot metadata."""
        service = ConversationService()

        message = service.create_message(
            content="Bot response",
            message_type=MessageType.BOT,
            conversation_id=sample_conversation.id,
            response_time_ms=250,
            model_used="test-model",
        )

        assert message is not None
        assert message.message_type == MessageType.BOT
        assert message.response_time_ms == 250
        assert message.model_used == "test-model"

    def test_create_message_updates_conversation(self, sample_conversation):
        """Test that creating message updates conversation timestamp."""
        service = ConversationService()

        # Get original updated_at
        original_updated = sample_conversation.updated_at

        # Create a message (this might take a moment)
        import time

        time.sleep(0.01)  # Small delay to ensure timestamp difference

        conversation_id = sample_conversation.id
        assert conversation_id is not None

        message = service.create_message(
            content="Test message", message_type=MessageType.USER, conversation_id=conversation_id
        )

        assert message is not None

        # Get updated conversation
        updated_conversation = service.get_conversation(sample_conversation.id)
        assert updated_conversation is not None
        assert updated_conversation.updated_at > original_updated

    def test_create_message_invalid_conversation(self, new_db):
        """Test message creation with invalid conversation."""
        service = ConversationService()

        message = service.create_message(content="Test", message_type=MessageType.USER, conversation_id=99999)

        assert message is None

    def test_get_conversation_messages(self, sample_conversation):
        """Test getting messages for a conversation."""
        service = ConversationService()

        # Create messages
        msg1 = service.create_message("First message", MessageType.USER, sample_conversation.id)
        msg2 = service.create_message("Second message", MessageType.BOT, sample_conversation.id)
        assert msg1 is not None and msg2 is not None

        messages = service.get_conversation_messages(sample_conversation.id)

        assert len(messages) == 2
        # Should be ordered by created_at asc (oldest first)
        assert messages[0].id == msg1.id
        assert messages[1].id == msg2.id

    def test_get_conversation_messages_with_limit(self, sample_conversation):
        """Test getting messages with limit."""
        service = ConversationService()

        # Create multiple messages
        for i in range(5):
            service.create_message(f"Message {i}", MessageType.USER, sample_conversation.id)

        messages = service.get_conversation_messages(sample_conversation.id, limit=3)

        assert len(messages) == 3

    def test_get_conversation_messages_empty(self, sample_conversation):
        """Test getting messages for conversation with none."""
        service = ConversationService()

        messages = service.get_conversation_messages(sample_conversation.id)

        assert messages == []

    def test_get_conversation_with_messages(self, sample_conversation):
        """Test getting conversation with all messages."""
        service = ConversationService()

        # Create messages
        msg1 = service.create_message("User message", MessageType.USER, sample_conversation.id)
        msg2 = service.create_message(
            "Bot response", MessageType.BOT, sample_conversation.id, response_time_ms=150, model_used="test-model"
        )
        assert msg1 is not None and msg2 is not None

        result = service.get_conversation_with_messages(sample_conversation.id)

        assert result is not None
        assert result.id == sample_conversation.id
        assert result.title == sample_conversation.title
        assert result.user_id == sample_conversation.user_id
        assert result.is_active == sample_conversation.is_active

        # Check messages
        assert len(result.messages) == 2

        # Check message details
        user_msg = result.messages[0]
        assert user_msg.content == "User message"
        assert user_msg.message_type == MessageType.USER
        assert isinstance(user_msg.created_at, str)  # Should be ISO format

        bot_msg = result.messages[1]
        assert bot_msg.content == "Bot response"
        assert bot_msg.message_type == MessageType.BOT
        assert bot_msg.response_time_ms == 150
        assert bot_msg.model_used == "test-model"

    def test_get_conversation_with_messages_not_found(self, new_db):
        """Test getting non-existent conversation with messages."""
        service = ConversationService()

        result = service.get_conversation_with_messages(99999)

        assert result is None

    def test_update_conversation_title(self, sample_conversation):
        """Test updating conversation title."""
        service = ConversationService()

        updated_conversation = service.update_conversation_title(sample_conversation.id, "Updated Title")

        assert updated_conversation is not None
        assert updated_conversation.title == "Updated Title"
        assert updated_conversation.updated_at > sample_conversation.updated_at

    def test_update_conversation_title_not_found(self, new_db):
        """Test updating title of non-existent conversation."""
        service = ConversationService()

        result = service.update_conversation_title(99999, "New Title")

        assert result is None

    def test_delete_conversation(self, sample_conversation):
        """Test soft-deleting a conversation."""
        service = ConversationService()

        success = service.delete_conversation(sample_conversation.id)

        assert success

        # Conversation should still exist but be inactive
        conversation = service.get_conversation(sample_conversation.id)
        assert conversation is not None
        assert not conversation.is_active

    def test_delete_conversation_not_found(self, new_db):
        """Test deleting non-existent conversation."""
        service = ConversationService()

        success = service.delete_conversation(99999)

        assert not success

    def test_global_service_instance(self):
        """Test that global service instance works."""
        assert conversation_service is not None
        assert isinstance(conversation_service, ConversationService)

    def test_complete_workflow(self, new_db):
        """Test complete conversation workflow."""
        service = ConversationService()

        # Create user
        user = service.get_or_create_user("workflow_user", "Workflow User")
        assert user is not None and user.id is not None

        # Create conversation
        conversation = service.create_conversation(user.id, "Workflow Test")
        assert conversation is not None and conversation.id is not None

        # Add messages
        user_msg = service.create_message("Hello", MessageType.USER, conversation.id)
        bot_msg = service.create_message(
            "Hi there!", MessageType.BOT, conversation.id, response_time_ms=100, model_used="test"
        )
        assert user_msg is not None and bot_msg is not None

        # Get conversation with messages
        full_conversation = service.get_conversation_with_messages(conversation.id)
        assert full_conversation is not None
        assert len(full_conversation.messages) == 2

        # Update title
        updated = service.update_conversation_title(conversation.id, "Updated Workflow Test")
        assert updated is not None
        assert updated.title == "Updated Workflow Test"

        # Get user conversations
        conversations = service.get_user_conversations(user.id)
        assert len(conversations) == 1
        assert conversations[0].title == "Updated Workflow Test"

        # Soft delete
        success = service.delete_conversation(conversation.id)
        assert success

        # Should not appear in active conversations
        active_conversations = service.get_user_conversations(user.id, active_only=True)
        assert len(active_conversations) == 0

        # But should appear in all conversations
        all_conversations = service.get_user_conversations(user.id, active_only=False)
        assert len(all_conversations) == 1
        assert not all_conversations[0].is_active
