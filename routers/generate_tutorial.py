# from fastapi import APIRouter, HTTPException
# # from chatbot_config import model
from chatbot_config import client
# from models import ChatbotRequest
# from langchain.memory.buffer import ConversationBufferMemory

# from fastapi.responses import StreamingResponse

import os
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langchain.memory.buffer_window import ConversationBufferWindowMemory
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chains import ConversationChain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from models import ChatbotRequest
from groq import Groq
import asyncio
from typing import AsyncGenerator

router = APIRouter()

CHAT_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template("You are a helpful assistant."),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}"),
    ]
)

class StreamingConversationChain:
    def __init__(self, temperature: float = 0.0):
        self.memories = {}
        self.temperature = temperature

    def generate_response(self, conversation_id: str, message: str):
    # async def generate_response(self, conversation_id: str, message: str) -> AsyncGenerator[str, None]:

        print("generating responses")

        memory = self.memories.get(conversation_id)
        if memory is None:
            memory = ConversationBufferWindowMemory(k=10)
            self.memories[conversation_id] = memory
        print(self.memories[conversation_id])

        # callback_handler = AsyncIteratorCallbackHandler()

        # chain = ConversationChain(
        #     memory=memory,
        #     prompt=CHAT_PROMPT_TEMPLATE,
        #     llm=None, 
        # )

        # async def run_chain():
        #     response = client.chat.completions.create(
        #         messages=memory.get_messages() + [{"role": "user", "content": message}],
        #         model="llama3-8b-8192",
        #     )
        #     return response

        # run = asyncio.create_task(run_chain())
        # async for token in callback_handler.aiter():
        #     yield token

        # await run

        print("lets goooo")

streaming_conversation_chain = StreamingConversationChain()


@router.post('/generate_tutorial/')
def generate_tutorial(request: ChatbotRequest):

    # Try getting generated response from configured gemini model
    try:
        # Extract player details
        name = request.player_details.name
        age = request.player_details.age
        position = request.player_details.position

        # Generate chat completion using Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Player details: name is {name}, age is {str(age)}, position is {position}. {request.prompt}",
                }
            ],
            model="llama3-8b-8192",
        )
        tutorial = chat_completion.choices[0].message.content

        conversation_id = f"{request.player_details.name}-{request.player_details.age}-{request.player_details.position}"
        streaming_conversation_chain.generate_response(conversation_id, request.prompt)

        return {"tutorial": tutorial}
    
        # # Generate response using StreamingConversationChain
        # return StreamingResponse(
        #     streaming_conversation_chain.generate_response(conversation_id, request.prompt),
        #     media_type="text/event-stream",
        # )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
