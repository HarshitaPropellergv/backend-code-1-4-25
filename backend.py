import os
import csv
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero, turn_detector
from livekit.plugins.aws.tts import TTS as PollyTTS
from livekit.plugins.aws.stt import STT as TranscribeSTT
from livekit.plugins import deepgram

import redis
import time


from services.loader import load_service
import json

load_dotenv(dotenv_path=".env.local")
# CONFIG_PATH = "config.json"

# def load_config():
#     with open(CONFIG_PATH, "r") as f:
#         return json.load(f)

# CONFIG = load_config()

# # Load the selected LLM dynamically
# selected_llm = CONFIG["llm"]["selected"]

# Connect to Azure Redis
redis_client = redis.StrictRedis(
    # host='your-redis-name.redis.cache.windows.net',
    host='RedisLivekit.redis.cache.windows.net',
    port=6380,
    # password='your-access-key',
    password='zpir55fUl0BFP6cBXykbyWqfHN1ZBj22AAzCaF6YHSQ=',
    ssl=True,
    decode_responses=True,
    db=0
)
DEFAULT_LANGUAGE = "English"
redis_client.set("selected_lang", DEFAULT_LANGUAGE)
DEFAULT_CONTEXT = "hello, my name is Abhilash"
redis_client.set("context", DEFAULT_CONTEXT)

# llm_model_selected = "cerebras"
# llm_model_selected="groq"
# llm_model_selected="openai"
# llm_model_selected=redis_client.get()
# tts_model_selected ="cartesia"#---api key limit
# tts_model_selected = "openai"
# tts_model_selected="elevenlabs"
# tts_model_selected="polly"
stt_model_selected = "deepgram"
# stt_model_selected = "deepgram"
# stt_model_selected = "openai"
# languageselected="English (US)"

# voicename="coral"#openai-gpt4o-mini-tts
# voicename="indianwoman"#cartesia
# voicename="Bella"#elevenlabs
# voicename= "Kajal"#polly


cerebras_api_key = os.getenv("CEREBRAS_API_KEY")

# llm_model = openai.llm.LLM.with_cerebras(
#         model="llama3.1-8b",
#         temperature=0.8,
#         api_key=cerebras_api_key
#     )
# tts_model=openai.TTS(
#         # model="tts-1",
#         model="gpt-4o-mini-tts",
#         voice="shimmer",
#         # speed=0.95,  #slower for more warmth
#         speed=1.5,  #faster for more energy
#         # instructions=instructions1,
#         # api_key=openai_api_key 
#     )
# stt_model= deepgram.stt.STT(
#         model="nova-2-general",
#         interim_results=True,
#         smart_format=True,
#         punctuate=True,
#         filler_words=True,
#         profanity_filter=False,
#         keywords=[("LiveKit", 3.5)],
#         language="hi",
#         # language="hi",
#         )

# try:

#     llm_model = load_service("llm", llm_model_selected)
#     print(f"✅ LLM Loaded: {llm_model}")
# except Exception as e:
#     print(f"❌ Error: {e}")

# -------------------- LOAD ENV VARIABLES -------------------- #
 
# -------------------- AWS CONFIGURATION -------------------- #
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
# aws_region = os.getenv("AWS_REGION", "us-east-1")
 
# -------------------- STT & TTS PLUGINS (Amazon) -------------------- #
amazon_stt = TranscribeSTT(
    speech_region="us-east-1",
    api_key=aws_access_key,
    api_secret=aws_secret_key,
    sample_rate=48000,
    language="en-IN",
    encoding="pcm",
    enable_partial_results_stabilization=True,
    partial_results_stability="high",
    show_speaker_label=False,
)
 
polly_tts = PollyTTS(
    voice="Kajal",
    language="en-IN",
    speech_engine="generative",
    sample_rate=16000,
    speech_region="us-east-1",
    api_key=aws_access_key,
    api_secret=aws_secret_key,
)
from livekit.plugins.cartesia import tts
cartesia_tts =tts.TTS(

            model="sonic-2",
            voice="3b554273-4299-48b9-9aaf-eefd438e3941",
            speed=-0.2,
            # speed = 0.3
            # emotion=["angry:high"]
        )
# -------------------- LOGGING SETUP -------------------- #
logger = logging.getLogger("voice-assistant")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
 
# # CSV Log File
# LOG_FILE = "metrics_log.csv"
 
# if not os.path.exists(LOG_FILE):
#     with open(LOG_FILE, "w", newline="") as f:
#         writer = csv.writer(f)
#         writer.writerow([
#             "Timestamp", "Sequence_ID", "STT_Audio_Duration", "STT_Duration",
#             "LLM_TTFT", "LLM_Input_Tokens", "LLM_Output_Tokens", "LLM_Tokens_Per_Sec",
#             "TTS_TTFB", "TTS_Audio_Duration", "EOU_Delay", "Transcription_Delay",
#             "Total_Latency"
#         ])
 
# -------------------- HELPER FUNCTION TO LOG METRICS -------------------- #
# def log_metrics(sequence_id, mtrcs: metrics.AgentMetrics):
#     with open(LOG_FILE, "a", newline="") as f:
#         writer = csv.writer(f)
#         writer.writerow([
#             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sequence_id,
#             getattr(mtrcs, "stt_audio_duration", "N/A"),
#             getattr(mtrcs, "stt_duration", "N/A"),
#             getattr(mtrcs, "llm_ttft", "N/A"),
#             getattr(mtrcs, "llm_prompt_tokens", "N/A"),
#             getattr(mtrcs, "llm_completion_tokens", "N/A"),
#             getattr(mtrcs, "llm_tokens_per_second", "N/A"),
#             getattr(mtrcs, "tts_ttfb", "N/A"),
#             getattr(mtrcs, "tts_audio_duration", "N/A"),
#             getattr(mtrcs, "end_of_utterance_delay", "N/A"),
#             getattr(mtrcs, "transcription_delay", "N/A"),
#             getattr(mtrcs, "total_latency", "N/A"),
#         ])
 
# -------------------- INITIALIZATION -------------------- #
 
 
 
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
 
async def entrypoint(ctx: JobContext):
    """Main function that runs the AI voice agent."""
 
    speech_rate = os.getenv("POLLY_SPEECH_RATE", "130%")  # Default to 130%
   
    # Define the SSML-based system instructions with human-like expressiveness
    # system_instructions = "Role: You are a professional AI consultant named Adam from Propeller Global Ventures, a Mumbai-based AI technology consulting firm. Your primary objective is to provide clear, concise, and goal-oriented responses while keeping the conversation focused." \
    # "Behavior:" \
    # "Concise & Precise: Keep answers short and direct while ensuring clarity." \
    # "Gentle Redirection: If the caller drifts off-topic, acknowledge their query briefly, answer it in one or two sentences, and politely steer the conversation back to the main topic." \
    # "Professional & Engaging: Maintain a friendly but authoritative tone that ensures the caller stays engaged while respecting time efficiency." \
    # "Example Conversation Flow" \
    # "Caller: “Oh, by the way, do you think AI will replace all jobs in the next 10 years?”" \
    # "AI Agent: “That’s an interesting discussion! While AI is evolving, it enhances human roles rather than replacing them. Speaking of AI solutions, let's get back to how we can optimize your tech strategy at Propeller Global Ventures.”" \
    # "Caller: “Got it! But I also wanted to ask—do you offer web development services too?”" \
    # "AI Agent: “We specialize in AI consulting, but we can connect you with the right experts. Now, coming back to your AI project, what specific challenges are you facing?”"
    print("/n /n hiiiii /n \n \n ")
    # system_instructions = await redis_client.get("context")
    system_instructions = redis_client.get("context") or " "
    languageselected = redis_client.get("selected_lang") or "English"
    tts_model_selected_value = redis_client.get("selected_tts_provider") or "openai"    
    tts_model_selected = tts_model_selected_value.lower()
    # tts_model_selected = "cartesia"
    voicename = redis_client.get("selected_voice") or "shimmer"
    # voicename = "Kajal"
    selected_llm_value = redis_client.get("selected_llm") or "openai"
    selected_llm = selected_llm_value.lower()
 
  
    
    print(f"\n--------------------------- language selected {languageselected} -------------------------------\n")
    print(f"\n--------------------------- stt model selected {stt_model_selected} -------------------------------\n")
    print(f"\n --------------------------voice  selected {voicename} ----------------------------------- \n")
    print(f"\n --------------------------llm selected {selected_llm} ----------------------------------- \n")
    print(f"\n --------------------------tts model selected {tts_model_selected} ----------------------------------- \n")
    llm_model = load_service("llm",selected_llm)
    stt_model = load_service("stt",stt_model_selected,language=languageselected)
    tts_model = load_service("tts", tts_model_selected, voice=voicename)
    initial_ctx = llm.ChatContext().append(role="system", text=system_instructions)

    

    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
 
    participant = await ctx.wait_for_participant()
    logger.info(f"Starting assistant for participant {participant.identity}")
    
    # Initialize the agent with SSML
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        # stt=amazon_stt,
        stt =stt_model,
        # llm=openai.LLM.with_groq(),
        llm = llm_model,
        tts=tts_model,
        # tts = cartesia_tts,
        chat_ctx=initial_ctx,
        #turn_detector=turn_detector.EOUModel(),
        min_endpointing_delay=0.1,
       # noise_cancellation=noise_cancellation.NC(),
        # noise_cancellation=noise_cancellation.BVC(),
       
       
       
    )
 
    agent.start(ctx.room, participant)
 
    usage_collector = metrics.UsageCollector()
 
    @agent.on("metrics_collected")
    def on_metrics_collected(mtrcs: metrics.AgentMetrics):
    #     sequence_id = mtrcs.sequence_id  
    #     log_metrics(sequence_id, mtrcs)
        usage_collector.collect(mtrcs)
 
    async def log_usage():
        """Logs final aggregated metrics at session end."""
        summary = usage_collector.get_summary()
        logger.info(f"{summary}")
        # log_metrics("SESSION-END", summary)
 
    ctx.add_shutdown_callback(log_usage)
 
    # -------------------- CHAT HANDLING -------------------- #
    chat = rtc.ChatManager(ctx.room)
 
async def answer_from_text(txt: str):
    chat_ctx = agent.chat_ctx.copy()
    chat_ctx.append(role="user", text=txt)
    stream = agent.llm.chat(chat_ctx=chat_ctx)
 
    # Proper SSML Formatting for Natural Speech
    ssml_text = f"""
    <speak>
        <amazon:auto-breaths volume="medium">
            <prosody rate="120%" pitch="high">
                <break time="500ms"/> {stream}
            </prosody>
        </amazon:auto-breaths>
    </speak>
    """.strip()  # Ensure no extra spaces at the beginning/end
 
    logger.info(f"TTS Output (SSML): {ssml_text}")  # Debugging to verify correct SSML
 
    # Ensure Polly understands it's SSML
    await agent.say(ssml_text, text_type="ssml", allow_interruptions=True)
 
 
    @chat.on("message_received")
    def on_chat_received(msg: rtc.ChatMessage):
        if msg.message:
            asyncio.create_task(answer_from_text(msg.message))
 
# -------------------- START WORKER -------------------- #
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
 