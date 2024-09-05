"""
memory_store.py
In-memory store initialized, prompt is pipelined into our model, and Runnable with 
session history is initialized
"""
from sqlalchemy.orm import Session
from models import ChatHistory
from config import model
from langchain_core.chat_history import BaseChatMessageHistory


import psycopg
import uuid
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_postgres import PostgresChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import json

# TODO make more secure
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
    ("system", "You are a helpful soccer assistant."),
    MessagesPlaceholder(variable_name="messages"),
])

table_name = 'chat_histories'

# Define a function to retrieve the chat history for a session
def get_session_history(session_id: str):
    history = PostgresChatMessageHistory(
        table_name,
        session_id,
        sync_connection=conn
    )
    print("Session history:", history.messages)
    return history

# Create the Runnable with the chat history and prompt template
chain = prompt | model
with_message_history = RunnableWithMessageHistory(chain, get_session_history)

# session_id = str(uuid.uuid4())

# # Print the result from invoking the runnable
# result = with_message_history.invoke([], config={"configurable": {"session_id": session_id}})
# print("Result from with_message_history.invoke:", result)



# print("RunnableWithMessageHistory initialized with chain and session history function.")

# # Test the functionality with a sample message
# test_message = HumanMessage(content="How do I improve my dribbling skills?")
# result = with_message_history.invoke([test_message], config={"configurable": {"session_id": session_id}})
# print("Result from test invocation:", result)