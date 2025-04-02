# THIS FILE IS AGENT.PY + SLIDING WINDOW MEMORY + BG NOISE
#stt, llm, tts:
#deepgram, openai, openai (4o-mini)
 
 
 
from __future__ import annotations
 
import asyncio
import logging
from dotenv import load_dotenv
import json
import os
# import azure.cognitiveservices.speech as speechsdk
from time import perf_counter
from typing import Annotated
from livekit import rtc, api
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    tokenize,
  
)
from livekit.agents.pipeline import VoicePipelineAgent,AgentTranscriptionOptions
from livekit.plugins import deepgram, openai, silero,cartesia
# from livekit.plugins.aws.stt import STT as TranscribeSTT
from livekit.agents.tokenize.basic import WordTokenizer, SentenceTokenizer
# from livekit.plugins.openai import tts  # Import OpenAI's TTS module
from livekit.agents import metrics
from livekit.rtc import AudioSource, AudioTrack
import numpy as np
import wave
from pathlib import Path
import uuid
 
import pandas as pd
#for sliding window
from collections import deque
# from typing import AsyncIterable

# from livekit.plugins import noise_cancellation


# load environment variables, this is optional, only used for local development
load_dotenv(dotenv_path=".env.local")#replace if you have .env
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

# openai_api_key = os.getenv("OPENAI_API_KEY")
cerebras_api_key = os.getenv("CEREBRAS_API_KEY")
# groq_api_key = os.getenv("GROQ_API_KEY")
# rime_api_key = os.getenv("RIME_API_KEY")



from services.loader import load_service
import json

CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

CONFIG = load_config()

# Load the selected LLM dynamically
selected_llm = CONFIG["llm"]["selected"]
tts_service = load_service("tts", CONFIG["tts"]["selected_provider"], voice=CONFIG["tts"]["selected_voice"])

try:
    llm_model = load_service("llm", selected_llm)
    print(f"✅ LLM Loaded: {llm_model}")
except Exception as e:
    print(f"❌ Error: {e}")
# Add this class after your imports and before the SlidingWindowMemory class
class AudioHandler:
    def __init__(self, sample_rate=48000, channels=1, track_id=None):
        self.audio_source = rtc.AudioSource(sample_rate, channels)
        self.track_id = track_id or f"audio_{str(uuid.uuid4())[:8]}"
        self.audio_track = rtc.LocalAudioTrack.create_audio_track(self.track_id, self.audio_source)
        self.audio_task = None
        self.audio_running = asyncio.Event()
       
    async def start_audio(self, wav_path: Path | str, volume: float = 0.4):
        self.audio_running.set()
        self.audio_task = asyncio.create_task(self._play_audio(wav_path, volume))
       
    async def stop_audio(self):
        """Stop audio playback immediately"""
        self.audio_running.clear()
        if self.audio_task:
            await self.audio_task
            self.audio_task = None
           
    async def _play_audio(self, wav_path: Path | str, volume: float):
        samples_per_channel = 9600
        wav_path = Path(wav_path)
       
        while self.audio_running.is_set():
            with wave.open(str(wav_path), 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                num_channels = wav_file.getnchannels()
               
                audio_data = wav_file.readframes(wav_file.getnframes())
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
               
                if num_channels == 2:
                    audio_array = audio_array.reshape(-1, 2).mean(axis=1)
               
                for i in range(0, len(audio_array), samples_per_channel):
                    if not self.audio_running.is_set():
                        break
                   
                    chunk = audio_array[i:i + samples_per_channel]
                   
                    if len(chunk) < samples_per_channel:
                        chunk = np.pad(chunk, (0, samples_per_channel - len(chunk)))
                   
                    chunk = np.tanh(chunk / 32768.0) * 32768.0
                    chunk = np.round(chunk * volume).astype(np.int16)
                   
                    await self.audio_source.capture_frame(rtc.AudioFrame(
                        data=chunk.tobytes(),
                        sample_rate=48000,
                        samples_per_channel=samples_per_channel,
                        num_channels=1
                    ))
                   
                    await asyncio.sleep((samples_per_channel / 48000) * 0.98)
   
    async def publish_track(self, room):
        await room.local_participant.publish_track(
            self.audio_track,
            rtc.TrackPublishOptions(
                source=rtc.TrackSource.SOURCE_MICROPHONE,
                stream=self.track_id
            )
        )
 

#sliding window ki class
class SlidingWindowMemory:
    def __init__(self, size: int):
        #initialize the sliding window with a fixed size
        #deque will discard the oldest entry when limit is reached
        self.size = size
        self.memory = deque(maxlen=size)
 
    def add_conversation(self, conversation: str):
        #add a new convo to the memory
        #the oldest convo will be removed once the limit is reached
        self.memory.append(conversation)
 
    def get_memory(self):
        #retrieve the list of convos currently in memory
        return list(self.memory)
 
 
#intiializing memory function (size define karna hai)
memory = SlidingWindowMemory(size=5)
 
 
 
#RAG
def load_knowledge_base() -> Dict[str, Any]:
    try:
        with open('knowledge_base.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Knowledge base file not found!")
        return {"company_info": {}}
    except json.JSONDecodeError:
        logger.error("Invalid JSON in knowledge base!")
        return {"company_info": {}}
 
 
#RAG
knowledge_base = load_knowledge_base()
 
outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")

 
_default_instructions = (
    # """you are a loan collection agent, you have to make sure to remind the user to pay the installment in time,\n you have to inform user about the loan installment firmly, you can be strict,direct and harsh if required but maintain professionalism."""
    f"""
     - You are Manvi, a loan collection agent. Your task is to remind users to pay their loan installments on time. you have to sound authoritive while maintaining professionalism.  
    - **For guidance:** Provide clear instructions with a firm and authoritive tone.  
    - **For strict actions and awareness:** Use commanding language to ensure urgency and compliance.  
    - **For empathy:** Show understanding but reinforce the importance of timely payments. 
    - **Do Not include any code related responses in the llm response example FN_CALL=False etc.
    - speak in english untill user says to speak in hindi.
    - if user says to speak in hindi: use **Hindi-English mix** (Hinglish) for natural communication. Avoid fully formal or Sanskritized Hindi, do NOT give response like first speaking in hindi then same sentence in english.   
    Keep responses concise (5-12 words). Complete sentences only.   
 
    """
)
async def entrypoint(ctx: JobContext):
    global _default_instructions, outbound_trunk_id
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    

    user_identity = "phone_user"
    phone_number = ctx.job.metadata
    logger.info(f"dialing {phone_number} to room {ctx.room.name}")
 
    instructions = (
        _default_instructions
        + "\nYou must always respond as Maanvi and never echo back what the user says. "
        + "Always provide helpful responses based on the context. "
        + "Start by introducing yourself and asking for the customer's name."
    )
 
    await ctx.api.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            room_name=ctx.room.name,
            sip_trunk_id=outbound_trunk_id,
            sip_call_to=phone_number,
            participant_identity=user_identity,
        )
    )
 
    participant = await ctx.wait_for_participant(identity=user_identity)
   
    # Initialize audio handler
    audio_handler = AudioHandler()
    await audio_handler.publish_track(ctx.room)
  
    agent = run_voice_pipeline_agent(ctx, participant, instructions, memory)

 
    
    #-----------------------metrics------------
    usage_collector = metrics.UsageCollector()
    metrics_df = pd.DataFrame()
    eou_delay = None
    llm_ttft = None
    tts_ttfb = None
    seq_id = None
    LLM_input_tokens = None
    LLM_output_tokens = None
    LLM_tokens_per_second=None
    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        nonlocal eou_delay,llm_ttft,tts_ttfb,seq_id,metrics_df,LLM_input_tokens,LLM_output_tokens,LLM_tokens_per_second
        metrics.log_metrics(mtrcs)
        usage_collector.collect(mtrcs)
        if isinstance(mtrcs, metrics.PipelineEOUMetrics):
            eou_delay = mtrcs.end_of_utterance_delay
            if seq_id == None:
                seq_id = mtrcs.sequence_id
        elif isinstance(mtrcs, metrics.PipelineLLMMetrics):
            llm_ttft = mtrcs.ttft
            LLM_input_tokens= mtrcs.prompt_tokens
            LLM_output_tokens= mtrcs.completion_tokens
            LLM_tokens_per_second=mtrcs.tokens_per_second
            if seq_id == None:
                seq_id = mtrcs.sequence_id
        elif isinstance(mtrcs, metrics.PipelineTTSMetrics):
            tts_ttfb = mtrcs.ttfb
            if seq_id == None:
                seq_id = mtrcs.sequence_id
        
        


        if eou_delay is not None and llm_ttft is not None and tts_ttfb is not None:
            total_latency = eou_delay + llm_ttft + tts_ttfb
            logger.info(f"Total Latency: {total_latency}")
            metrics_df=pd.DataFrame([
                {
            "Sequenceid":seq_id,
            "eou_delay":eou_delay,
            "llm_ttft":llm_ttft,
            "LLM_input_tokens":LLM_input_tokens,
            "LLM_output_tokens":LLM_output_tokens,
            "LLM_tokens_per_second":LLM_tokens_per_second,
            "tts_ttfb":tts_ttfb,
            "total_latency":total_latency

                }
            ])
            print(metrics_df)
            file_exists = os.path.exists("sonic-2-metrics1.csv")
            metrics_df.to_csv("sonic-2-metrics1.csv", mode='a', index=False, header=not file_exists)
            eou_delay=None
            llm_ttft = None
            tts_ttfb = None
            seq_id = None
            LLM_input_tokens = None
            LLM_output_tokens = None
            LLM_tokens_per_second=None

    start_time = perf_counter()
    while perf_counter() - start_time < 30:
        call_status = participant.attributes.get("sip.callStatus")
        if call_status == "active":
            logger.info("Call is active, starting agent and background audio...")
           
            await audio_handler.start_audio("cafe_noise.wav")
            await asyncio.sleep(1)
           
            await agent.say("Hello, this is Maanvi, calling from propeller bank..", allow_interruptions=True)
            # await agent.say("Hello?", allow_interruptions=True)
            logger.info("User has picked up, agent and audio started")
           
            # Stay in conversation until call ends
            try:
                log_counter = 0
                while not participant.disconnect_reason:
                    if log_counter % 50 == 0:  # Log every 5 seconds (50 * 0.1s sleep)
                        logger.info("Call active, agent running...")
                    log_counter += 1
                    await asyncio.sleep(0.1)
                logger.info("Call ended naturally")
            except Exception as e:
                logger.error(f"Error during conversation: {e}")
            break
           
        elif call_status == "automation":
            pass
        elif participant.disconnect_reason:
            logger.info("Call ended, stopping background audio...")
            await audio_handler.stop_audio()
            break
        await asyncio.sleep(0.1)
 
    logger.info("Session ended, cleaning up")
    await audio_handler.stop_audio()
    ctx.shutdown()
 

 
class CallActions(llm.FunctionContext):
    """
    Detect user intent and perform actions
    """
 
    def __init__(
        self, *, api: api.LiveKitAPI, participant: rtc.RemoteParticipant, room: rtc.Room
    ):
        super().__init__()
 
        self.api = api
        self.participant = participant
        self.room = room
 
    async def hangup(self):
        try:
            await self.api.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=self.room.name,
                    identity=self.participant.identity,
                )
            )
        except Exception as e:
            # it's possible that the user has already hung up, this error can be ignored
            logger.info(f"received error while ending call: {e}")
 
    @llm.ai_callable()
    async def end_call(self):
        """Called when the user wants to end the call"""
        logger.info(f"ending the call for {self.participant.identity}")
        await self.hangup()

 
#STT:
 
deepgram_stt = deepgram.stt.STT(
    model="nova-2-general",
    interim_results=True,
    smart_format=True,
    punctuate=True,
    filler_words=True,
    profanity_filter=False,
    keywords=[("LiveKit", 3.5)],
    language="en",
    # language="hi",
)

# aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
# aws_speech_engine = "standard" #change accordingly neural,standard
# aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
# aws_region = os.getenv("AWS_REGION", "us-east-1")
# amazon_stt = TranscribeSTT(
#     speech_region=aws_region,
#     api_key=aws_access_key,
#     api_secret=aws_secret_key,
#     sample_rate=48000,
#     language="en-US",
#     encoding="pcm",
#     enable_partial_results_stabilization=True,
#     partial_results_stability="high",
#     show_speaker_label=False,
# )
 
# openai_stt = openai.stt.STT(
#   language="en",
#   model="whisper-1",#gpt-4o-mini-transcribe
#   noise_reduction_type="far_field"

# ) 

def run_voice_pipeline_agent(
    ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str, memory: SlidingWindowMemory
):
    logger.info("starting voice pipeline agent")
 
    # Include memory context in the initial chat context
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=instructions + "\nMemory Context:\n" + "\n".join(memory.get_memory()),
    )
    
    # async def truncate_context(agent: VoicePipelineAgent, chat_ctx: llm.ChatContext):
    #     logger.info(f"------------{chat_ctx.messages}--------\nlength_of_chat:{len(chat_ctx.messages)}")
    #     if len(chat_ctx.messages) > 10:
    #         chat_ctx.messages = chat_ctx.messages[:-2]
    #         logger.info(f"-----------------after -3\n{chat_ctx.messages}")
    # async def truncate_context(agent: VoicePipelineAgent, chat_ctx: llm.ChatContext):
    #     logger.info(f"------------{chat_ctx.messages}--------\nlength_of_chat:{len(chat_ctx.messages)}")

    #     # Ensure we always keep the system message
    #     system_message = next((msg for msg in chat_ctx.messages if msg.role == 'system'), None)

    #     # Remove all assistant messages first if length exceeds 5
    #     chat_ctx.messages = [msg for msg in chat_ctx.messages if msg.role != 'assistant']

    #     # If still exceeding, keep the system message and the latest user messages
    #     while len(chat_ctx.messages) > 5:
    #         chat_ctx.messages.pop(1)  # Remove older messages, keeping the latest ones

    #     # Ensure the system message remains the first item
    #     if system_message and system_message not in chat_ctx.messages:
    #         chat_ctx.messages.insert(0, system_message)

    #     logger.info(f"-----------------after truncation\n{chat_ctx.messages}")
    
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=ctx.proc.userdata["stt"],
        llm=ctx.proc.userdata["llm"],
        tts=ctx.proc.userdata["tts"],  # Using the prewarmed OpenAI TTS
        # turn_detector=turn_detector.EOUModel(),
        min_endpointing_delay=0.0001,
        interrupt_min_words=0,
        # noise_cancellation=noise_cancellation.NC(),
        # max_endpointing_delay=3,
        # allow_interruptions=True,
        # interrupt_speech_duration=0.5,
        chat_ctx=initial_ctx,
        preemptive_synthesis=True,
        # before_llm_cb=truncate_context,
        # transcription=AgentTranscriptionOptions(
        #     user_transcription=True,  # Enable user STT transcriptions
        #     agent_transcription=True,  # Enable AI-generated transcriptions
        #     agent_transcription_speed=1.0,  # Control transcription processing speed
        #     sentence_tokenizer=ctx.proc.userdata["sentence_tokenizer"],  
        #     word_tokenizer=ctx.proc.userdata["word_tokenizer"], 
        #     hyphenate_word=lambda word: word.replace("-", " "),  # Optional: Modify word tokenization rules
        # ),
        # before_tts_cb=_before_tts_cb,
        fnc_ctx=CallActions(api=ctx.api, participant=participant, room=ctx.room),
        
    )
 
    agent.start(ctx.room, participant)
    return agent
 
 

instructions1 = """
**Voice Affect:**  
Authoritative yet composed—firm but not aggressive. Speak like an experienced Indian loan collector woman who understands financial struggles but does not tolerate delays. Maintain professionalism with a touch of warmth when necessary.  

**Tone:**  
Authoritive,Direct, urgency and seriousness without unnecessary harshness. If required, be firm but always professional. When guiding, maintain a helpful and understanding tone.  

**Pacing:**  
Deliberate and steady; slightly faster when stressing deadlines or consequences. Maintain a controlled rhythm

**Emotion:**  
Authoritive,Serious, non-negotiable, and firm. Show deep **understanding** for genuine concerns but remain **unyielding** when enforcing deadlines. If the borrower is unresponsive, escalate the strictness while keeping it professional.  

**Pronunciation:**  
Sharp and precise, with a strong Indian-English accent. Emphasize critical words like **"deadline," "overdue," "penalty," "legal action," "final notice"** to reinforce urgency while keeping composure.  

**Pauses:**  
Minimal—only enough for the borrower to absorb the message. No long silences that suggest leniency.  

**Emphasis:**  
Clearly highlight warnings and consequences:  

- **"Your installment is overdue—please clear it immediately to avoid penalties."**  
- **"Delays will lead to serious consequences, including legal action."**  
- **"This is your FINAL reminder. Pay now to avoid further issues."**  
- **"We understand difficulties, but commitments must be honored. Please act now."**  

**Dialect:**  
Strong Indian-English accent with well-paced delivery. Firm yet calm, ensuring both urgency and professionalism.  

**Overall Approach:**  
Be **firm yet warm**—strict when necessary, but always professional and respectful. Provide **guidance and solutions** while leaving **no room for excuses.** The goal is **compliance with a human touch.**  

"""

 
#PREWARM FUNCTION:
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load(
        min_speech_duration = 0.05, #0.05,
        min_silence_duration = 0.2, #0.55,
        prefix_padding_duration = 0.2, #0.5,
        max_buffered_speech = 60.0, #60.0,
        activation_threshold = 0.2, #0.5,
        sample_rate = 16000
    )
   
    # proc.userdata["stt"] = deepgram.stt.STT(
    #     model="nova-2-general",
    #     language="en-US",
    # )
    
    # proc.userdata["stt"] = openai.stt.STT(
    # language="en",
    # model="gpt-4o-mini-transcribe",
    # # noise_reduction_type="near_field",
    # api_key=openai_api_key 

    # ) 

    proc.userdata["stt"]=deepgram_stt
    # proc.userdata["stt"]=amazon_stt

    # Simplified OpenAI TTS configuration with only supported parameters
    # proc.userdata["tts"] = openai.TTS(
    #     # model="tts-1",
    #     model="gpt-4o-mini-tts",
    #     voice="coral",
    #     # speed=0.95,  #slower for more warmth
    #     speed=1.5,  #faster for more energy
    #     instructions=instructions1,
    #     api_key=openai_api_key 
    # )
    # proc.userdata["tts"] = rime.TTS(
    #     model="mist",
    #     speaker="rainforest",
    #     speed_alpha=0.9,
    #     reduce_latency=True,
    #     api_key = rime_api_key
    #     )

    proc.userdata["tts"] = cartesia.TTS(
        model="sonic-2",
        voice="3b554273-4299-48b9-9aaf-eefd438e3941",
        speed=-0.2,
        # speed = 0.3
        # emotion=["angry:high"]
    )
   
    # proc.userdata["llm"] = openai.LLM.with_groq(
    #     model="llama3-8b-8192",
    #     api_key=groq_api_key
    # )

    # proc.userdata["llm"] = openai.llm.LLM.with_cerebras(
    #     model="llama3.1-8b",
    #     temperature=0.8,
    #     api_key=cerebras_api_key
    # )
    proc.userdata["llm"]=llm_model

    # proc.userdata["llm"] = openai.LLM.with_azure(
    #     model="gpt-4o-mini",
    #     temperature=0.8,
       
    # )
    # proc.userdata["llm"] = openai.LLM(
    #     model="gpt-4o-mini",
    #     api_key=openai_api_key
        
    # )
    

    # proc.userdata["llm"] = aws.LLM(
    #     model = "Bedrock"
    #     api_key=aws_access_key,
    #     api_secret=aws_secret_key,
    #     region = 'us-east-1',

    #     )

    # proc.userdata["word_tokenizer"] = WordTokenizer()  # Prewarm tokenizer
    # proc.userdata["sentence_tokenizer"] = SentenceTokenizer()
    # proc.userdata["turn_detector"] = turn_detector.EOUModel()
 
 
 
 
if __name__ == "__main__":
    if not outbound_trunk_id or not outbound_trunk_id.startswith("ST_"):
        raise ValueError(
            "SIP_OUTBOUND_TRUNK_ID is not set."
        )
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # giving this agent a name will allow us to dispatch it via API
            # automatic dispatch is disabled when `agent_name` is set
            agent_name="outbound-caller",
            # prewarm by loading the VAD model, needed only for VoicePipelineAgent
            prewarm_fnc=prewarm,
        )
    )
 
 
 
 
 
# Nakshatra: lk dispatch create --new-room --agent-name outbound-caller --metadata '+919891398961'
# Ashish: lk dispatch create --new-room --agent-name outbound-caller --metadata '+919021342078'
# Harshita: lk dispatch create --new-room --agent-name outbound-caller --metadata '+919326842596'
# Aayush: lk dispatch create --new-room --agent-name outbound-caller --metadata '+919137425804'
# Himanshu: lk dispatch create --new-room --agent-name outbound-caller --metadata '+447423714557'