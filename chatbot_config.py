import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA

nvapi_key = os.getenv('NVAPI_KEY')
if not nvapi_key:
    raise ValueError("API key not found")

client = ChatNVIDIA(
    model="meta/llama3-70b-instruct",
    api_key=nvapi_key
)

# for chunk in client.stream([{"role":"user","content":"Write a limerick about the wonders of GPU computing."}]): 
#   print(chunk.content, end="")