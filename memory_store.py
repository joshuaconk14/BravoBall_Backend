from chatbot_config import model
from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

store = {}

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpfuls assistant who knows soccer.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

chain = prompt | model

with_message_history = RunnableWithMessageHistory(chain, get_session_history)