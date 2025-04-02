from livekit.plugins.aws.stt import STT as TranscribeSTT
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")
 
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

def load(language="English"):
    lang_map = {
        "English": "en-IN",
        "Hindi": "hi-IN",
        "Tamil":"ta-IN",
        "Japanese":"ja-JP",
    }
    language_selected = lang_map.get(language,lang_map["English"])
    # language_selected=lang_map.get(language)
    amazon_stt = TranscribeSTT(
        speech_region="us-east-1",
        api_key=aws_access_key,
        api_secret=aws_secret_key,
        sample_rate=48000,
        language=language_selected,
        encoding="pcm",
        enable_partial_results_stabilization=True,
        partial_results_stability="high",
        show_speaker_label=False,
    )

    return amazon_stt
