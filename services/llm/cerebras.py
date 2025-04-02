from livekit.plugins import openai
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")#replace if you have .env
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)
 
# openai_api_key = os.getenv("OPENAI_API_KEY")
cerebras_api_key = os.getenv("CEREBRAS_API_KEY")
def load():
    # print(f"\nloading cerebras\n")
    cerebras_llm = openai.llm.LLM.with_cerebras(
        model="llama3.1-8b",
        temperature=0.8,
        api_key=cerebras_api_key
    )
    return  cerebras_llm

