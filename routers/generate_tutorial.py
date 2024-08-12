from chatbot_config import model
from fastapi import APIRouter, HTTPException
from models import ChatbotRequest

from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage



router = APIRouter()

print("initialized")

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

with_message_history = RunnableWithMessageHistory(model, get_session_history)


@router.post('/generate_tutorial/')
def generate_tutorial(request: ChatbotRequest):
    try:
        config = {"configurable": {"session_id": "abc"}}

        response = with_message_history.invoke(
            HumanMessage(content=request.prompt),
            config=config
        )

        return {"tutorial": response.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
    
