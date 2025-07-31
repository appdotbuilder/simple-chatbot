"""
Tests for chatbot service functionality.
"""

import pytest
from app.chatbot_service import ChatbotService, chatbot_service
from app.conversation_service import conversation_service
from app.models import MessageType
from app.database import reset_db


@pytest.fixture()
def new_db():
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def sample_conversation(new_db):
    """Create a test user and conversation."""
    user = conversation_service.get_or_create_user("test_user", "Test User")
    assert user is not None
    assert user.id is not None

    conversation = conversation_service.create_conversation(user.id, "Test Chat")
    assert conversation is not None
    assert conversation.id is not None

    return conversation


class TestChatbotService:
    """Test chatbot service functionality."""

    def test_chatbot_service_initialization(self):
        """Test chatbot service initializes correctly."""
        service = ChatbotService()
        assert service.model_name == "simple-chatbot-v1.0"

    def test_generate_response_greetings(self):
        """Test greeting response generation."""
        service = ChatbotService()

        greetings = ["hello", "hi", "hey", "good morning"]
        for greeting in greetings:
            response = service.generate_response(greeting)
            assert isinstance(response, str)
            assert len(response) > 0
            # Should contain welcoming language
            assert any(word in response.lower() for word in ["hello", "hi", "help", "great"])

    def test_generate_response_questions(self):
        """Test question response generation."""
        service = ChatbotService()

        # Test specific questions
        response = service.generate_response("How are you?")
        assert "doing great" in response.lower() or "how are you" in response.lower()

        response = service.generate_response("What's your name?")
        assert "chatbot" in response.lower() or "name" in response.lower()

        response = service.generate_response("What's the weather like?")
        assert "weather" in response.lower()

        # Generic questions
        response = service.generate_response("Why is the sky blue?")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_response_emotions(self):
        """Test emotional response generation."""
        service = ChatbotService()

        # Sad emotions
        sad_messages = ["I'm feeling sad", "I'm upset", "I'm frustrated"]
        for message in sad_messages:
            response = service.generate_response(message)
            # Should provide supportive response - might be default or specific
            assert len(response) > 0
            assert isinstance(response, str)

        # Happy emotions
        happy_messages = ["I'm so happy!", "This is awesome!", "I feel great"]
        for message in happy_messages:
            response = service.generate_response(message)
            # Should provide appropriate response
            assert len(response) > 0
            assert isinstance(response, str)

    def test_generate_response_help_requests(self):
        """Test help request responses."""
        service = ChatbotService()

        help_messages = ["Can you help me?", "I need assistance", "Support please"]
        for message in help_messages:
            response = service.generate_response(message)
            # Should provide helpful response
            assert len(response) > 0
            assert isinstance(response, str)

    def test_generate_response_thanks(self):
        """Test thank you responses."""
        service = ChatbotService()

        thank_messages = ["Thank you", "Thanks!", "Thank you so much"]
        for message in thank_messages:
            response = service.generate_response(message)
            # Should provide appropriate acknowledgment
            assert len(response) > 0
            assert isinstance(response, str)

    def test_generate_response_goodbyes(self):
        """Test goodbye responses."""
        service = ChatbotService()

        goodbye_messages = ["Goodbye", "Bye!", "See you later", "Talk to you later"]
        for message in goodbye_messages:
            response = service.generate_response(message)
            # Should provide farewell response
            assert len(response) > 0
            assert isinstance(response, str)

    def test_generate_response_default(self):
        """Test default responses for unmatched input."""
        service = ChatbotService()

        # Random messages that don't match specific patterns
        random_messages = [
            "The weather is nice today",
            "I like pizza",
            "Programming is interesting",
            "Random statement here",
        ]

        for message in random_messages:
            response = service.generate_response(message)
            assert isinstance(response, str)
            assert len(response) > 0
            # Should be a valid response (content will vary)

    def test_create_bot_message(self, sample_conversation):
        """Test bot message creation."""
        service = ChatbotService()

        message = service.create_bot_message(
            content="Test bot response", conversation_id=sample_conversation.id, response_time_ms=150
        )

        assert message is not None
        assert message.id is not None
        assert message.content == "Test bot response"
        assert message.message_type == MessageType.BOT
        assert message.conversation_id == sample_conversation.id
        assert message.response_time_ms == 150
        assert message.model_used == "simple-chatbot-v1.0"

    def test_create_bot_message_invalid_conversation(self, new_db):
        """Test bot message creation with invalid conversation ID."""
        service = ChatbotService()

        message = service.create_bot_message(
            content="Test response",
            conversation_id=99999,  # Non-existent conversation
        )

        # Should handle error gracefully
        assert message is None

    def test_process_user_message(self, sample_conversation):
        """Test complete user message processing."""
        service = ChatbotService()

        bot_message = service.process_user_message(user_message="Hello there!", conversation_id=sample_conversation.id)

        assert bot_message is not None
        assert bot_message.id is not None
        assert bot_message.message_type == MessageType.BOT
        assert bot_message.conversation_id == sample_conversation.id
        assert bot_message.response_time_ms is not None
        assert bot_message.response_time_ms >= 0
        assert bot_message.model_used == "simple-chatbot-v1.0"

        # Response should be appropriate for greeting
        assert any(word in bot_message.content.lower() for word in ["hello", "hi", "help"])

    def test_process_user_message_invalid_conversation(self, new_db):
        """Test processing message with invalid conversation."""
        service = ChatbotService()

        bot_message = service.process_user_message(user_message="Hello", conversation_id=99999)

        # Should handle error gracefully - may return None or error message
        if bot_message is not None:
            assert "error" in bot_message.content.lower()
        # If None, that's also acceptable error handling

    def test_global_service_instance(self):
        """Test that global service instance works."""
        assert chatbot_service is not None
        assert isinstance(chatbot_service, ChatbotService)

        response = chatbot_service.generate_response("Hello")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_response_variety(self):
        """Test that responses have some variety."""
        service = ChatbotService()

        # Generate multiple responses for the same input
        responses = []
        for _ in range(10):
            response = service.generate_response("Tell me something interesting")
            responses.append(response)

        # Should have some variety (not all identical)
        unique_responses = set(responses)
        assert len(unique_responses) > 1, "Responses should have some variety"

    def test_response_length_reasonable(self):
        """Test that responses are reasonable length."""
        service = ChatbotService()

        test_messages = ["Hello", "How are you?", "This is a longer message with more context and details", "?"]

        for message in test_messages:
            response = service.generate_response(message)
            # Responses should be reasonable length (not empty, not too long)
            assert 5 <= len(response) <= 500, f"Response length {len(response)} not reasonable for '{message}'"

    def test_case_insensitive_matching(self):
        """Test that pattern matching is case insensitive."""
        service = ChatbotService()

        # Test different cases
        responses = []
        responses.append(service.generate_response("HELLO"))
        responses.append(service.generate_response("hello"))
        responses.append(service.generate_response("Hello"))
        responses.append(service.generate_response("HeLLo"))

        # All should trigger greeting responses
        for response in responses:
            assert any(word in response.lower() for word in ["hello", "hi", "help", "great"])

    def test_empty_message_handling(self, sample_conversation):
        """Test handling of empty or whitespace messages."""
        service = ChatbotService()

        # Test with empty string
        response = service.generate_response("")
        assert isinstance(response, str)
        assert len(response) > 0

        # Test with whitespace
        response = service.generate_response("   ")
        assert isinstance(response, str)
        assert len(response) > 0
