from memory_store import with_message_history, memory_store
from fastapi import APIRouter, HTTPException
from models import ChatbotRequest
from langchain_core.messages import HumanMessage

# Initialize router for 'generate_tutorial' endpoint handler
router = APIRouter()

print("initialized")

@router.post('/generate_tutorial/')
def generate_tutorial(request: ChatbotRequest):
    '''
    This decorated function listens for POST requests made to server and returns
    a Llama3 response based on user input in ChatbotRequest
    '''
    try:
        session_id = "user123"
        config = {"configurable": {"session_id": session_id}}
        prompt = request.prompt

        response = with_message_history.invoke(
            [HumanMessage(content=prompt)],
            config=config,
        )

        return {"tutorial": response.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
    
