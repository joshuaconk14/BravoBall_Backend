import os
from chatbot_config import client, groq_chat
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain.memory.buffer_window import ConversationBufferWindowMemory
from langchain.callbacks import AsyncIteratorCallbackHandler
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

from langchain_core.runnables.history import RunnableWithMessageHistory



router = APIRouter()

print("initialized")

conversation_chain = ConversationChain(
    llm=groq_chat,
    memory=ConversationBufferWindowMemory(k=10),  # Keep the last 2 interactions in memory
    verbose=True
)

@router.post('/generate_tutorial/')
def generate_tutorial(request: ChatbotRequest):
    try:
        # Create the input based on the player's details and prompt
        # input_text = f"Player details: name is {request.player_details.name}, age is {str(request.player_details.age)}, position is {request.player_details.position}. {request.prompt}"
        input_text = f"{request.prompt}"


        # Use the ConversationChain to predict the response
        response = conversation_chain.predict(input=input_text)

        return {"tutorial": response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
    

# router = APIRouter()

# conversational_memory_length = 10

# memory = ConversationBufferWindowMemory(k=conversational_memory_length, memory_key="chat_history", return_messages=True)
# system = "You are a helpful assistant."
# human = "{text}"
# prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])

# conversation = LLMChain(
#     llm=groq_chat,  # The Groq LangChain chat object initialized earlier.
#     prompt=prompt,  # The constructed prompt template.
#     verbose=True,   # Enables verbose output, which can be useful for debugging.
#     memory=memory,  # The conversational memory object that stores and manages the conversation history.
# )

# history = StreamlitChatMessageHistory(key="chat_messages")


# @router.post('/generate_tutorial/')
# def generate_tutorial(request: ChatbotRequest):

#     try:
#         # Extract player details
#         name = request.player_details.name
#         age = request.player_details.age
#         position = request.player_details.position
#         user_question = request.prompt

#         # # Generate chat completion using Groq
#         # chat_completion = client.chat.completions.create(
#         #     messages=[
#         #         {
#         #             "role": "user",
#         #             "content": f"Player details: name is {name}, age is {str(age)}, position is {position}. {request.prompt}. Keep response short.",
#         #         }
#         #     ],
#         #     model="llama3-8b-8192",
#         # )
#         # tutorial = chat_completion.choices[0].message.content

#         tutorial = conversation.predict(human_input=user_question)
#         message = {'human':user_question,'AI':tutorial}
#         print(message)

#         return {"tutorial": tutorial}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
    