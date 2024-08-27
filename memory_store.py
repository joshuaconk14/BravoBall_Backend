# """
# memory_store.py
# In-memory store initialized, prompt is pipelined into our model, and Runnable with 
# session history is initialized
# """

# from sqlalchemy.orm import Session
# from models import ChatHistory
# from db import get_db
# from config import model
# from langchain_core.chat_history import BaseChatMessageHistory
# from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from datetime import datetime


# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             "You are a helpful soccer assistant that gives concise responses.",
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
# )

# max_messages = 10

# class DatabaseChatMessageHistory(BaseChatMessageHistory):
#     def __init__(self, session_id: str, db: Session):
#         self.session_id = session_id
#         self.db = db

#     def add_message(self, message):
#         chat_history = ChatHistory(
#             session_id=self.session_id,
#             message=message.content,
#             timestamp=datetime.utcnow()
#         )
#         self.db.add(chat_history)
#         self.db.commit()

#     def clear(self):
#         self.db.query(ChatHistory).filter(ChatHistory.session_id == self.session_id).delete()
#         self.db.commit()

#     @property
#     def messages(self):
#         return self.db.query(ChatHistory).filter(ChatHistory.session_id == self.session_id).order_by(ChatHistory.timestamp).all()

# def get_session_history(session_id: str) -> BaseChatMessageHistory:
#     print("get_session_history")

#     db = next(get_db())
#     history = DatabaseChatMessageHistory(session_id, db)
#     # messages = history.messages
#     # # if len(messages) > max_messages:
#     # #     for message in messages[:-max_messages]:
#     # #         db.delete(message)
#     # #     db.commit()
#     return history

# chain = prompt | model

# with_message_history = RunnableWithMessageHistory(chain, get_session_history)




# """
# memory_store.py
# In-memory store initialized, prompt is pipelined into our model, and Runnable with 
# session history is initialized
# """

from sqlalchemy.orm import Session
from models import ChatHistory
from db import get_db
from config import model
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_postgres import PostgresChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime


# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             "You are a helpful soccer assistant that gives concise responses.",
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
# )

# max_messages = 10

# def get_session_history(session_id: str) -> BaseChatMessageHistory:
#     connection_string = "postgresql+asyncpg://jordinho:m44YMQsbrxpewhTJRzzX@localhost/chat_histories"
#     history = PostgresChatMessageHistory(
#         connection_string=connection_string,
#         session_id=session_id
#     )
#     return history

# chain = prompt | model

# with_message_history = RunnableWithMessageHistory(chain, get_session_history)
# print("RunnableWithMessageHistory initialized with chain and session history function.")


# # (Uncomment and provide appropriate values to test)
# session_id = "test_session"
# history = get_session_history(session_id)
# history.add_user_message("hi!")
# history.add_ai_message("whats up?")


import psycopg
import uuid
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_postgres import PostgresChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Define connection information
conn_info = {
    'host': 'localhost',
    'port': '5432',
    'database': 'tekkdb',
    'user': 'jordinho',
    'password': 'm44YMQsbrxpewhTJRzzX'
}

# Establish a synchronous connection to the database
try:
    conn = psycopg.connect(
        host=conn_info['host'],
        port=conn_info['port'],
        dbname=conn_info['database'],
        user=conn_info['user'],
        password=conn_info['password']
    )
    print("Connection to PostgreSQL established successfully.")
except psycopg.OperationalError as e:
    print(f"Error connecting to PostgreSQL: {e}")

# Define the prompt template with placeholders
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful soccer assistant that gives concise responses."),
    MessagesPlaceholder(variable_name="messages"),
])

# Define a function to retrieve the chat history for a session
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    return PostgresChatMessageHistory(
        'chat_histories',  # Assuming 'chat_histories' is your table name
        session_id,
        sync_connection=conn  # Pass the established connection
    )

# Create a session ID for the current interaction
session_id = str(uuid.uuid4())
print(f"Session ID: {session_id}")

# Initialize the chat history manager for the session
chat_history = get_session_history(session_id)

# Create the Runnable with the chat history and prompt template
chain = prompt | model  # Assuming 'model' is your AI model configured elsewhere
with_message_history = RunnableWithMessageHistory(chain, get_session_history)
print("RunnableWithMessageHistory initialized with chain and session history function.")

# Testing adding messages and invoking the runnable
chat_history.add_messages([
    SystemMessage(content="System: Hello! How can I help you with soccer today?"),
    HumanMessage(content="User: How do I improve my dribbling skills?")
])

print("printing result...")
# Invoke the runnable with the current messages and print the output
result = with_message_history.invoke([], config={"configurable": {"session_id": session_id}})
print("Result from with_message_history.invoke:", result)
