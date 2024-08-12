from chatbot_config import model
from fastapi import APIRouter, HTTPException
from models import ChatbotRequest

from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


router = APIRouter()

store = {}

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant specialized in soccer. Answer all questions to the best of your ability.",
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


print("initialized")

@router.post('/generate_tutorial/')
def generate_tutorial(request: ChatbotRequest):
    try:
        config = {"configurable": {"session_id": "abc"}}
        prompt = request.prompt

        response = with_message_history.invoke(
            [HumanMessage(content=prompt)],
            config=config,
        )

        return {"tutorial": response.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
    
