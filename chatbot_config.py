import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA

nvapi_key = os.getenv('NVAPI_KEY')
if not nvapi_key:
    raise ValueError("API key not found")

model = ChatNVIDIA(
    model="meta/llama3-70b-instruct",
    api_key=nvapi_key
)
