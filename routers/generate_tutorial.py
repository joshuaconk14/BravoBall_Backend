"""
generate_tutorial.py
Endpoint listening for POST requests from frontend, handles user questions and uses Runnable from
memory_store.py to communicate with Llama3, while integrating with a PostgreSQL database
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from models import ChatbotRequest, User, ChatHistory
from db import get_db
from memory_store import with_message_history
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.post('/generate_tutorial/')
async def generate_tutorial(request: ChatbotRequest, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(User).where(User.id == request.user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        session_id = request.session_id or str(uuid.uuid4())
        config = {"configurable": {"session_id": session_id}}
        prompt = request.prompt

        try:
            async with db.begin():
                user_message = ChatHistory(
                    user_id=user.id,
                    session_id=session_id,
                    message=prompt,
                    timestamp=datetime.utcnow(),
                    is_user=True
                )
                db.add(user_message)
                await db.flush()

                response = await with_message_history.invoke(
                    [HumanMessage(content=prompt)],
                    config=config,
                )

                ai_message = ChatHistory(
                    user_id=user.id,
                    session_id=session_id,
                    message=response.content,
                    timestamp=datetime.utcnow(),
                    is_user=False
                )
                db.add(ai_message)
        except Exception as tx_error:
            print(f"Transaction error: {tx_error}")
            raise HTTPException(status_code=500, detail=str(tx_error))

        return {"tutorial": response.content, "session_id": session_id}

    except Exception as e:
        print(f"Error in generate_tutorial: {e}")
        raise HTTPException(status_code=500, detail=str(e))
