from app.database import create_tables
import app.chatbot


def startup() -> None:
    # this function is called before the first request
    create_tables()
    app.chatbot.create()
