from livekit.plugins import openai

import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")
#replace if you have .env

def load(voice="shimmer"):
    instructions1 = "happy customer service agent"
    voice = voice.lower()
    # voicedict = {
    #     "indianwoman": "3b554273-4299-48b9-9aaf-eefd438e3941",
    #     "Sarah": "694f9389-aac1-45b6-b726-9d9369183238",
    #     }
    # voiceid = voicedict.get(voice,voicedict["indianwoman"])
    gpt_4o_mini_tts = openai.TTS(
        # model="tts-1",
        model="gpt-4o-mini-tts",
        voice=voice,
        # speed=0.95,  #slower for more warmth
        speed=1.5,  #faster for more energy
        instructions=instructions1,
        # api_key=openai_api_key 
    )
    return gpt_4o_mini_tts
