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
    ("system", "You are a helpful soccer assistant that gives concise responses."),
    MessagesPlaceholder(variable_name="messages"),
])


table_name = 'chat_histories'

# Define a function to retrieve the chat history for a session
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    return PostgresChatMessageHistory(
        table_name,
        session_id,
        sync_connection=conn
    )

# Create a session ID for the current interaction
session_id = str(uuid.uuid4())
print(f"Session ID: {session_id}")

# Initialize the chat history manager for the session
chat_history = get_session_history(session_id)

# Create the Runnable with the chat history and prompt template
chain = prompt | model  # Assuming 'model' is your AI model configured elsewhere
with_message_history = RunnableWithMessageHistory(chain, get_session_history)


# # Print the result from invoking the runnable
# result = with_message_history.invoke([], config={"configurable": {"session_id": session_id}})
# print("Result from with_message_history.invoke:", result)





# print("RunnableWithMessageHistory initialized with chain and session history function.")

# # Testing adding messages and invoking the runnable
# chat_history.add_messages([
#     SystemMessage(content="System: Hello! How can I help you with soccer today?"),
#     HumanMessage(content="User: How do I improve my dribbling skills?")
# ])

# print("printing result...")
# # Invoke the runnable with the current messages and print the output
# result = with_message_history.invoke([], config={"configurable": {"session_id": session_id}})
# print("Result from with_message_history.invoke:", result)
    

#############################

# """
# memory_store.py
# In-memory store initialized, prompt is pipelined into our model, and Runnable with 
# session history is initialized
# """
# from sqlalchemy.orm import Session
# from models import ChatHistory
# from config import model
# from langchain_core.chat_history import BaseChatMessageHistory


# import psycopg
# import uuid
# from pprint import pprint
# import asyncio

# from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
# from langchain_postgres import PostgresChatMessageHistory
# from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


# # Define the prompt template with placeholders
# prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are a helpful soccer assistant that gives concise responses."),
#     MessagesPlaceholder(variable_name="messages"),
# ])

# # Pipe prompt into model
# runnable = prompt | model

# table_name = 'chat_histories'
# session_id = str(uuid.uuid4())

# async_connection = None

# # TODO make private info more secure
# async def init_async_connection():
#     global async_connection
#     async_connection = await psycopg.AsyncConnection.connect(
#         user="jordinho",
#         password='m44YMQsbrxpewhTJRzzX',
#         dbname='tekkdb',
#         host="localhost",
#         port=5432)

# async def aget_session_history(session_id: str) -> BaseChatMessageHistory:
#     return PostgresChatMessageHistory(
#         table_name,
#         session_id,
#         async_connection=async_connection
#     )

# awith_message_history = RunnableWithMessageHistory(
#     runnable,
#     aget_session_history,
#     input_messages_key="input",
#     history_messages_key="history",
# )

# async def amain():
#     await init_async_connection()
#     result = await awith_message_history.ainvoke(
#         {"ability": "math", "input": "What does cosine mean?"},
#         config={"configurable": {"session_id": str(uuid.uuid4())}},
#     )
#     pprint(result)

# asyncio.run(amain())