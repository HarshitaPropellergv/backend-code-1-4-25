from livekit.plugins import deepgram
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")

def load(language="English"):
    lang_map = {
        "English": "en-IN",
        "Hindi": "hi",
    }
    language_selected = lang_map.get(language,lang_map["English"])
    deepgram_stt = deepgram.stt.STT(
        model="nova-2-general",
        interim_results=True,
        smart_format=True,
        punctuate=True,
        filler_words=True,
        profanity_filter=False,
        keywords=[("LiveKit", 3.5)],
        language=language_selected,
        # language="hi",
        )

    return deepgram_stt