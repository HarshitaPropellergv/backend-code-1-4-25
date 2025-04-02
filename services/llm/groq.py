from livekit.plugins import openai
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")#replace if you have .env
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

groq_api_key = os.getenv("GROQ_API_KEY")

def load():
    # print(f"\nloading cerebras\n")
    groq_llm = openai.LLM.with_groq(
        model="llama3-8b-8192",
        api_key=groq_api_key
    )
    return  groq_llm

