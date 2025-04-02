from livekit.plugins import openai
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")
 
# aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
# aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
def load(language="English"):
    lang_map = {
        "English": "en",
        "Hindi": "hi-IN",
    }
    language_selected = lang_map.get(language,lang_map["English"])
    openai_stt = openai.stt.STT(
    language=language_selected,
    model="whisper-1",
    # noise_reduction_type="far_field",

    ) 

    return openai_stt

 