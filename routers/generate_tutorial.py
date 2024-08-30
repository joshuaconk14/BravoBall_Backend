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
from db import aget_db
from memory_store import with_message_history
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.post('/generate_tutorial/')
async def generate_tutorial(request: ChatbotRequest, db: AsyncSession = Depends(aget_db)):
    # Start transaction
    transaction = await db.begin()
    try:
        print("GOT HERE1")
        stmt = select(User).where(User.id == request.user_id)
        result = await db.execute(stmt)
        print("GOT HERE2")
        user = result.scalars().first()

        if not user:
            await transaction.rollback()  # Ensure to rollback on error
            raise HTTPException(status_code=404, detail="User not found")

        print("GOT HERE3")

        session_id = request.session_id or str(uuid.uuid4())
        config = {"configurable": {"session_id": session_id}}
        prompt = request.prompt

        print("GOT HERE 4")
        user_message = ChatHistory(
            user_id=user.id,
            session_id=session_id,
            message=prompt,
            timestamp=datetime.utcnow(),
            is_user=True
        )
        db.add(user_message)
        await db.flush()

        print("GOT HERE 5")
        try:
            print("Config:", config)
            print("Input:", [HumanMessage(content=prompt)])
            response = await with_message_history.invoke(
                [HumanMessage(content=prompt)],
                config=config,
            )
            print("Response:", response)
        except Exception as e:
            print("Error during model invocation:", str(e))
            print("Error type:", type(e))
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

        print("GOT HERE 6")
        ai_message = ChatHistory(
            user_id=user.id,
            session_id=session_id,
            message=response.content,
            timestamp=datetime.utcnow(),
            is_user=False
        )
        db.add(ai_message)
        await db.commit()  # Commit all changes after successful operations

        return {"tutorial": response.content, "session_id": session_id}

    except Exception as e:
        await transaction.rollback()  # Rollback on any exception
        print(f"Error in generate_tutorial: {e}")
        raise HTTPException(status_code=500, detail=str(e))
