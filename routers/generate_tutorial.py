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
from models import ChatbotRequest, PlayerDetails
from groq import Groq
import asyncio
from typing import Dict, AsyncGenerator

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory


router = APIRouter()


# # In-memory store for session history
# conversation_histories: Dict[str, ConversationBufferWindowMemory] = {}

# def get_conversation_history(conversation_id: str) -> BaseChatMessageHistory:
#     """
#     This function returns the conversation history if it exists. If it doesn't, create a new one
#     with conversation_id as the key and a buffer window capacity of 10.
#     """
#     if conversation_id not in conversation_histories:
#         conversation_histories[conversation_id] = ConversationBufferWindowMemory(k=10)
#     return conversation_histories[conversation_id]

message_buffer = ""
print("initialized buffer")

@router.post('/generate_tutorial/')
# @router.post('/generate_tutorial/', response_class=StreamingResponse)
def generate_tutorial(request: ChatbotRequest):

    # TODO dont really wont global
    global message_buffer

    try:
        # Extract player details
        name = request.player_details.name
        age = request.player_details.age
        position = request.player_details.position
        conversation_id = f"{name}-{age}-{position}"

        # # Get reference to or create conversation history
        # memory = get_conversation_history(conversation_id)

        # # Add current user input into the conversation history
        # memory.add_message({"role": "user", "content": request.prompt})
        
        # messages = memory.get_messages()

        # Generate chat completion using Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    # "content": f"Player details: name is {name}, age is {str(age)}, position is {position}. {request.prompt}. Keep response short.",
                    "content": f"{request.prompt}. Keep response short.",

                }
            ],
            # messages=messages,

            model="llama3-8b-8192",
        )
        tutorial = chat_completion.choices[0].message.content

        # conversation_id = f"{request.player_details.name}-{request.player_details.age}-{request.player_details.position}"
        # streaming_conversation_chain.generate_response(conversation_id, request.prompt)

        # memory.add_message({"role": "assistant", "content": tutorial})

        if len(message_buffer) > 200:
            message_buffer = ""
        message_buffer += tutorial
        print(message_buffer)

        return {"tutorial": tutorial}
    
        # # Generate response using StreamingConversationChain
        # return StreamingResponse(
        #     streaming_conversation_chain.generate_response(conversation_id, request.prompt),
        #     media_type="text/event-stream",
        # )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")





# # This class stores memories and generates responses based on conversation memory through streaming response
# class StreamingConversationChain:
#     def __init__(self, temperature: float = 0.0):
#         self.memories = {}
#         self.temperature = temperature
#         self.llm = client.chat.completions
#         print("initialized")

#     def generate_response(self, conversation_id: str, message: str):
#     # async def generate_response(self, conversation_id: str, message: str) -> AsyncGenerator[str, None]:

#         print("generating responses")

#         memory = self.memories.get(conversation_id)
#         if memory is None:
#             memory = ConversationBufferWindowMemory(k=10)
#             self.memories[conversation_id] = memory
#         print(self.memories[conversation_id])

#         callback_handler = AsyncIteratorCallbackHandler()

#         chain = RunnableWithMessageHistory(
#             memory=memory,
#             prompt=CHAT_PROMPT_TEMPLATE,
#             llm=self.llm, 
#         )

#         response = self.llm.create(
#             messages=memory.get_messages() + [{"role": "user", "content": message}],
#             model="llama3-8b-8192",
#             stream=True,
#         )

#         for chunk in response:
#             if "choices" in chunk and len(chunk.choices) > 0:
#                 yield chunk.choices[0].delta.get('content', '')

#         print("lets goooo")


# streaming_conversation_chain = StreamingConversationChain()