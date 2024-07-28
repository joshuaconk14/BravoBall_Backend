import os
from groq import Groq
from functions import get_settings

try:
    groq_key = get_settings().groq_api_key
    if not groq_key:
        raise ValueError("API key not found")

    # Initialize Groq client
    client = Groq(api_key=groq_key)
    print(groq_key)
except Exception as e:
    print(f"An error occurred: {e}")

# # Initialize Groq client
# client = Groq(
#     api_key=groq_key,
# )

# print(groq_key)