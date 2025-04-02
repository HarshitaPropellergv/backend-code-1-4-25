from livekit.plugins import openai

def load():
    openai_llm = openai.LLM(
        model="gpt-4o-mini",
        # api_key=openai_api_key
        
    )
    return openai_llm