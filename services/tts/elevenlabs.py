from livekit.plugins import elevenlabs
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env.local")


def load(voice="Bella"):
    voicedict = {
        "Bella": "EXAVITQu4vr4xnSDxMaL",
        "Sarah": "EXAVITQu4vr4xnSDxMaL",
        }
    voiceid = voicedict.get(voice,voicedict["Bella"])
    eleven_tts=elevenlabs.tts.TTS(
        model="eleven_turbo_v2_5",
        voice=elevenlabs.tts.Voice(
            id=voiceid,
            name=voice,
            category="premade",
            settings=elevenlabs.tts.VoiceSettings(
                stability=0.71,
                similarity_boost=0.5,
                style=0.0,
                use_speaker_boost=True
            ),
        ),
        language="en",
        streaming_latency=3,
        enable_ssml_parsing=False,
        chunk_length_schedule=[80, 120, 200, 260],
    )
    return eleven_tts
