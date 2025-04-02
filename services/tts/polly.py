from livekit.plugins.aws.tts import TTS as PollyTTS
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")
 
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")


def load(voice="Kajal"):
    # voicedict = {
    #     "indianwoman": "3b554273-4299-48b9-9aaf-eefd438e3941",
    #     "Sarah": "694f9389-aac1-45b6-b726-9d9369183238",
    #     }
    # voiceid = voicedict.get(voice,voicedict["indianwoman"])
    polly_tts = PollyTTS(
        voice=voice,
        language="en-IN",
        speech_engine="generative",
        sample_rate=16000,
        speech_region="us-east-1",
        api_key=aws_access_key,
        api_secret=aws_secret_key,
    )
    return polly_tts