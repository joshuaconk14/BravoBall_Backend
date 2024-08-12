import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA

# Obtain NVIDIA api key
nvapi_key = os.getenv('NVAPI_KEY')
if not nvapi_key:
    raise ValueError("API key not found")

# Initialize ChatNVIDIA client to connect with Llama3
model = ChatNVIDIA(
    model="meta/llama3-70b-instruct",
    api_key=nvapi_key
)
