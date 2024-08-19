"""
generate_tutorial.py
Endpoint listening for POST requests from frontend, handles user questions and uses Runnable from
memory_store.py to communicate with Llama3
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models import ChatbotRequest
from langchain_core.messages import HumanMessage
from memory_store import with_message_history

router = APIRouter()

@router.post('/generate_tutorial/')
async def generate_tutorial(request: ChatbotRequest):
    try:
        # TODO make a better session ID for each conversation
        session_id = "user123"

        # Session ID in config identifies the user's unique conversation when Runnable is made
        config = {"configurable": {"session_id": session_id}}
        prompt = request.prompt 

        # Async streaming response to generate chunks for response so user can see updated response. Llama3 runnable invoked with astream
        async def generate():
            async for chunk in with_message_history.astream(
                [HumanMessage(content=prompt)],
                config=config,
            ):
                print("[" + chunk.content + "]")
                yield f"data: {chunk.content}\n\n"

        # Return Llama3 response as dictionary so frontend can read JSON payload
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
