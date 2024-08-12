from memory_store import with_message_history
from fastapi import APIRouter, HTTPException
from models import ChatbotRequest
from langchain_core.messages import HumanMessage

router = APIRouter()

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
    
