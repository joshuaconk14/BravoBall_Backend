from chatbot_config import model
from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# In-memory store for chatbot
memory_store = {}

# ChatPromptTemplate provides initial context for model
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpfuls assistant who knows soccer.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Max number of messages to hold in each conversation
max_messages = 10

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    '''
    This function creates a new conversation in 'memory_store' dictionary with 
    'session_id' as the key. Create a new one if it doesn't exist yet, or else
    make sure the size is limited to 10 message
    '''
    
    # If this is a new conversation, instantiate it
    if session_id not in memory_store:
        memory_store[session_id] = InMemoryChatMessageHistory()

    # Else conversation already exists, ensure conversation size is less than 10
    else:
        history = memory_store[session_id]
        if len(history.messages) > max_messages:
            history.messages = history.messages[-max_messages:]
    return memory_store[session_id]

# Chain pipelines the prompt into the model
chain = prompt | model

# Runnable instance with chain and function to obtain memory store every time it's invoked
with_message_history = RunnableWithMessageHistory(chain, get_session_history)
