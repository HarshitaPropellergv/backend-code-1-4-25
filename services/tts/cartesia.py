from livekit.plugins.cartesia import tts
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")
#replace if you have .env

def load(voice="indian woman"):
    voice=voice.lower()
    voicedict = {
        "indian woman": "3b554273-4299-48b9-9aaf-eefd438e3941",
        "zia": "32b3f3c5-7171-46aa-abe7-b598964aa793",
        "hindi woman":"9cebb910-d4b7-4a4a-85a4-12c79137724c"
        }
    voiceid = voicedict.get(voice,voicedict["indian woman"])
    cartesia_tts =tts.TTS(

            model="sonic-2",
            voice=voiceid,
            speed=-0.2,
            # speed = 0.3
            # emotion=["angry:high"]
        )
    return cartesia_tts