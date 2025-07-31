"""
Chatbot service module handling AI responses and conversation logic.
"""

import time
import random
from typing import Optional
from app.models import Message, MessageType, MessageCreate
from app.database import get_session
from logging import getLogger

logger = getLogger(__name__)


class ChatbotService:
    """Service for generating chatbot responses and handling conversation logic."""

    def __init__(self):
        self.model_name = "simple-chatbot-v1.0"

    def generate_response(self, user_message: str) -> str:
        """
        Generate a chatbot response based on user input.
        Uses simple rule-based responses for demonstration.
        """
        user_message_lower = user_message.lower().strip()

        # Greeting responses
        if any(greeting in user_message_lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            responses = [
                "Hello! How can I help you today?",
                "Hi there! What's on your mind?",
                "Hey! Great to see you. What can I do for you?",
                "Hello! I'm here to chat. What would you like to talk about?",
            ]
            return random.choice(responses)

        # Question responses
        if user_message_lower.endswith("?"):
            if "how are you" in user_message_lower:
                return "I'm doing great, thank you for asking! How are you doing today?"
            elif "what" in user_message_lower and "name" in user_message_lower:
                return "I'm your friendly chatbot assistant! You can call me ChatBot. What's your name?"
            elif "weather" in user_message_lower:
                return "I don't have access to real-time weather data, but I hope it's nice where you are! Is there anything else I can help you with?"
            elif "time" in user_message_lower:
                return "I don't have access to the current time, but you can check your device's clock. Is there something else I can assist you with?"
            else:
                responses = [
                    "That's an interesting question! Let me think about that...",
                    "Hmm, I'm not sure about that specific question, but I'd love to help you explore it further.",
                    "Great question! While I might not have the exact answer, I'm happy to discuss it with you.",
                ]
                return random.choice(responses)

        # Emotional responses
        if any(word in user_message_lower for word in ["sad", "upset", "angry", "frustrated"]):
            return "I'm sorry to hear you're feeling that way. Sometimes it helps to talk about what's bothering you. I'm here to listen."

        if any(word in user_message_lower for word in ["happy", "excited", "great", "awesome", "wonderful"]):
            return "That's wonderful to hear! I'm glad you're feeling positive. What's making you so happy?"

        # Help responses
        if any(word in user_message_lower for word in ["help", "assist", "support"]):
            return "I'm here to help! I can chat with you about various topics, answer questions, or just have a friendly conversation. What would you like to talk about?"

        # Thank you responses
        if any(word in user_message_lower for word in ["thank", "thanks"]):
            return "You're very welcome! I'm happy I could help. Is there anything else you'd like to chat about?"

        # Goodbye responses
        if any(word in user_message_lower for word in ["bye", "goodbye", "see you", "talk later"]):
            responses = [
                "Goodbye! It was great chatting with you. Have a wonderful day!",
                "See you later! Feel free to come back anytime you want to chat.",
                "Take care! I enjoyed our conversation. Come back soon!",
            ]
            return random.choice(responses)

        # Default responses for other messages
        default_responses = [
            "That's interesting! Tell me more about that.",
            "I see what you mean. What made you think about that?",
            "Thanks for sharing that with me! How do you feel about it?",
            "That sounds intriguing. Can you elaborate a bit more?",
            "I appreciate you telling me that. What's your perspective on it?",
            "Interesting point! I'd love to hear more of your thoughts on this.",
        ]

        return random.choice(default_responses)

    def create_bot_message(
        self, content: str, conversation_id: int, response_time_ms: Optional[int] = None
    ) -> Optional[Message]:
        """Create and save a bot message to the database."""
        try:
            with get_session() as session:
                message_data = MessageCreate(
                    content=content,
                    message_type=MessageType.BOT,
                    conversation_id=conversation_id,
                    response_time_ms=response_time_ms,
                    model_used=self.model_name,
                )
                message = Message(**message_data.model_dump())
                session.add(message)
                session.commit()
                session.refresh(message)

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
            logger.error(f"Failed to create bot message: {e}")
            return None

    def process_user_message(self, user_message: str, conversation_id: int) -> Optional[Message]:
        """
        Process a user message and generate a bot response.
        Returns the bot's response message.
        """
        start_time = time.time()

        try:
            # Generate response
            response_content = self.generate_response(user_message)

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Create and save bot message
            bot_message = self.create_bot_message(
                content=response_content, conversation_id=conversation_id, response_time_ms=response_time_ms
            )

            if bot_message:
                logger.info(f"Generated bot response for conversation {conversation_id} in {response_time_ms}ms")

            return bot_message

        except Exception as e:
            logger.error(f"Failed to process user message: {e}")
            # Return error message
            return self.create_bot_message(
                content="I'm sorry, I encountered an error while processing your message. Please try again.",
                conversation_id=conversation_id,
            )


# Global chatbot service instance
chatbot_service = ChatbotService()
