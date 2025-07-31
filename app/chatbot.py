"""
Chatbot UI module - main interface for the chatbot application.
"""

from nicegui import ui, app
from typing import Optional
from app.models import Message, MessageType, User, Conversation
from app.conversation_service import conversation_service
from app.chatbot_service import chatbot_service
from datetime import datetime
from logging import getLogger

logger = getLogger(__name__)


class ChatbotUI:
    """Main chatbot UI component managing the conversation interface."""

    def __init__(self):
        self.current_user: Optional[User] = None
        self.current_conversation: Optional[Conversation] = None
        self.message_container: Optional[ui.element] = None
        self.message_input: Optional[ui.input] = None
        self.conversation_list: Optional[ui.element] = None

    async def initialize_user(self) -> bool:
        """Initialize or get the current user from storage."""
        try:
            await ui.context.client.connected()

            # Get username from user storage, or create default
            username = app.storage.user.get("username")
            if not username:
                username = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                app.storage.user["username"] = username

            # Get or create user
            self.current_user = conversation_service.get_or_create_user(
                username=username, display_name=f"User {username}"
            )

            if not self.current_user:
                ui.notify("Failed to initialize user", type="negative")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to initialize user: {e}")
            ui.notify("Failed to initialize user session", type="negative")
            return False

    async def create_new_conversation(self) -> bool:
        """Create a new conversation for the current user."""
        if not self.current_user or self.current_user.id is None:
            return False

        try:
            self.current_conversation = conversation_service.create_conversation(
                user_id=self.current_user.id, title="New Chat"
            )

            if self.current_conversation:
                # Store current conversation ID in tab storage
                app.storage.tab["current_conversation_id"] = self.current_conversation.id
                ui.notify("Started new conversation", type="positive")
                return True
            else:
                ui.notify("Failed to create conversation", type="negative")
                return False

        except Exception as e:
            logger.error(f"Failed to create new conversation: {e}")
            ui.notify("Failed to create new conversation", type="negative")
            return False

    async def load_conversation(self, conversation_id: int) -> bool:
        """Load an existing conversation."""
        try:
            self.current_conversation = conversation_service.get_conversation(conversation_id)

            if self.current_conversation:
                app.storage.tab["current_conversation_id"] = conversation_id
                await self.refresh_messages()
                ui.notify("Conversation loaded", type="positive")
                return True
            else:
                ui.notify("Conversation not found", type="negative")
                return False

        except Exception as e:
            logger.error(f"Failed to load conversation {conversation_id}: {e}")
            ui.notify("Failed to load conversation", type="negative")
            return False

    async def send_message(self, content: str) -> None:
        """Send a user message and get bot response."""
        if not self.current_conversation or not content.strip():
            return

        if self.current_conversation.id is None:
            ui.notify("Invalid conversation", type="negative")
            return

        try:
            # Create user message
            user_message = conversation_service.create_message(
                content=content.strip(), message_type=MessageType.USER, conversation_id=self.current_conversation.id
            )

            if not user_message:
                ui.notify("Failed to send message", type="negative")
                return

            # Clear input
            if self.message_input:
                self.message_input.value = ""

            # Add user message to UI immediately
            await self.add_message_to_ui(user_message)

            # Generate bot response
            bot_message = chatbot_service.process_user_message(
                user_message=content.strip(), conversation_id=self.current_conversation.id
            )

            if bot_message:
                # Add bot message to UI
                await self.add_message_to_ui(bot_message)

                # Update conversation title if it's the first exchange
                if self.current_conversation.title == "New Chat":
                    # Use first few words of user message as title
                    title_words = content.strip().split()[:4]
                    new_title = " ".join(title_words)
                    if len(new_title) > 50:
                        new_title = new_title[:47] + "..."

                    conversation_service.update_conversation_title(self.current_conversation.id, new_title)
                    self.current_conversation.title = new_title
                    await self.refresh_conversation_list()
            else:
                ui.notify("Failed to get bot response", type="negative")

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            ui.notify("Failed to send message", type="negative")

    async def add_message_to_ui(self, message: Message) -> None:
        """Add a message to the UI display."""
        if not self.message_container:
            return

        with self.message_container:
            with ui.row().classes("w-full mb-4"):
                # Message alignment and styling based on type
                if message.message_type == MessageType.USER:
                    # User message - right aligned, blue
                    ui.space()  # Push to right
                    with ui.card().classes("bg-blue-500 text-white p-4 rounded-lg max-w-md"):
                        ui.label(message.content).classes("text-sm leading-relaxed")
                        ui.label(message.created_at.strftime("%H:%M")).classes("text-xs opacity-75 mt-1")
                else:
                    # Bot message - left aligned, gray
                    with ui.card().classes("bg-gray-100 text-gray-800 p-4 rounded-lg max-w-md"):
                        ui.label(message.content).classes("text-sm leading-relaxed")
                        with ui.row().classes("items-center gap-2 mt-1"):
                            ui.label(message.created_at.strftime("%H:%M")).classes("text-xs text-gray-500")
                            if message.response_time_ms:
                                ui.label(f"({message.response_time_ms}ms)").classes("text-xs text-gray-400")
                    ui.space()  # Push left

        # Scroll to bottom
        ui.run_javascript(
            'document.querySelector(".message-container").scrollTop = document.querySelector(".message-container").scrollHeight'
        )

    async def refresh_messages(self) -> None:
        """Refresh the message display."""
        if not self.message_container or not self.current_conversation or self.current_conversation.id is None:
            return

        try:
            # Clear existing messages
            self.message_container.clear()

            # Load messages from database
            messages = conversation_service.get_conversation_messages(self.current_conversation.id)

            # Add messages to UI
            for message in messages:
                await self.add_message_to_ui(message)

        except Exception as e:
            logger.error(f"Failed to refresh messages: {e}")
            ui.notify("Failed to load messages", type="negative")

    async def refresh_conversation_list(self) -> None:
        """Refresh the conversation list sidebar."""
        if not self.conversation_list or not self.current_user or self.current_user.id is None:
            return

        try:
            self.conversation_list.clear()

            with self.conversation_list:
                # New conversation button
                ui.button("New Chat", on_click=lambda: self.handle_new_conversation(), icon="add").classes(
                    "w-full mb-4 bg-blue-500 text-white hover:bg-blue-600"
                )

                # Load conversations
                conversations = conversation_service.get_user_conversations(self.current_user.id)

                if not conversations:
                    ui.label("No conversations yet").classes("text-gray-500 text-sm text-center p-4")
                else:
                    for conv in conversations:
                        is_current = self.current_conversation and conv.id == self.current_conversation.id

                        button_classes = "w-full text-left p-3 rounded hover:bg-gray-100 mb-2"
                        if is_current:
                            button_classes += " bg-blue-50 border-l-4 border-blue-500"

                        with ui.card().classes(button_classes + " cursor-pointer"):
                            with ui.column().classes("gap-1"):
                                ui.label(conv.title).classes("font-medium text-sm truncate")
                                ui.label(conv.updated_at.strftime("%m/%d %H:%M")).classes("text-xs text-gray-500")

                            # Add click handler
                            ui.run_javascript(f'''
                                document.querySelector('div[data-conv-id="{conv.id}"]').addEventListener('click', 
                                () => window.loadConversation({conv.id}))
                            ''')

                        # Set data attribute for JavaScript
                        ui.run_javascript(f"""
                            document.querySelector('.cursor-pointer:last-child').setAttribute('data-conv-id', '{conv.id}')
                        """)

        except Exception as e:
            logger.error(f"Failed to refresh conversation list: {e}")

    async def handle_new_conversation(self) -> None:
        """Handle new conversation creation."""
        if await self.create_new_conversation():
            await self.refresh_messages()
            await self.refresh_conversation_list()

    def create_ui(self) -> None:
        """Create the main chatbot UI."""
        # Apply modern theme
        ui.colors(
            primary="#2563eb",
            secondary="#64748b",
            accent="#10b981",
            positive="#10b981",
            negative="#ef4444",
            warning="#f59e0b",
            info="#3b82f6",
        )

        # Page title and styling
        ui.page_title("ChatBot - Your AI Assistant")

        with ui.row().classes("w-full h-screen"):
            # Sidebar for conversations
            with ui.column().classes("w-80 bg-gray-50 border-r border-gray-200 p-4 overflow-auto"):
                ui.label("Conversations").classes("text-lg font-bold mb-4 text-gray-800")
                self.conversation_list = ui.column().classes("w-full")

            # Main chat area
            with ui.column().classes("flex-1 flex flex-col h-full"):
                # Chat header
                with ui.row().classes("w-full p-4 bg-white border-b border-gray-200 items-center"):
                    ui.icon("smart_toy").classes("text-2xl text-blue-500")
                    ui.label("ChatBot Assistant").classes("text-xl font-bold text-gray-800 ml-2")
                    ui.space()
                    ui.label("Your friendly AI companion").classes("text-sm text-gray-500")

                # Messages area
                with ui.scroll_area().classes("flex-1 p-4 message-container"):
                    self.message_container = ui.column().classes("w-full")

                # Input area
                with ui.row().classes("w-full p-4 bg-white border-t border-gray-200 gap-2"):
                    self.message_input = (
                        ui.input(placeholder="Type your message here... (Press Enter to send)")
                        .classes("flex-1")
                        .props("outlined")
                    )
                    self.message_input.on(
                        "keydown.enter",
                        lambda: self.send_message(self.message_input.value if self.message_input else ""),
                    )

                    ui.button(
                        icon="send",
                        on_click=lambda: self.send_message(self.message_input.value if self.message_input else ""),
                    ).classes("bg-blue-500 text-white hover:bg-blue-600").props("round")

        # Add JavaScript for conversation loading
        ui.add_head_html("""
        <script>
            window.loadConversation = async function(conversationId) {
                // This will be handled by the Python backend
                console.log('Loading conversation:', conversationId);
            }
        </script>
        """)


# Global chatbot UI instance
chatbot_ui = ChatbotUI()


def create():
    """Create the chatbot application pages."""

    @ui.page("/")
    async def chatbot_page():
        """Main chatbot page."""
        # Initialize user session
        if not await chatbot_ui.initialize_user():
            ui.label("Failed to initialize chatbot session").classes("text-red-500 text-center p-8")
            return

        # Create or load conversation
        current_conv_id = app.storage.tab.get("current_conversation_id")
        if current_conv_id:
            # Try to load existing conversation
            if not await chatbot_ui.load_conversation(current_conv_id):
                # If loading fails, create new conversation
                await chatbot_ui.create_new_conversation()
        else:
            # Create new conversation
            await chatbot_ui.create_new_conversation()

        # Create the UI
        chatbot_ui.create_ui()

        # Initial UI refresh
        await chatbot_ui.refresh_conversation_list()
        await chatbot_ui.refresh_messages()

        # Welcome message for new conversations
        if chatbot_ui.current_conversation and chatbot_ui.current_conversation.id is not None:
            messages = conversation_service.get_conversation_messages(chatbot_ui.current_conversation.id)

            if not messages:
                # Add welcome message
                welcome_message = chatbot_service.create_bot_message(
                    content="Hello! I'm your AI chatbot assistant. I'm here to chat with you about anything you'd like to discuss. How can I help you today?",
                    conversation_id=chatbot_ui.current_conversation.id,
                )

                if welcome_message:
                    await chatbot_ui.add_message_to_ui(welcome_message)
