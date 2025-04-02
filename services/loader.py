import importlib
import json
import os

# Load Configuration
CONFIG_PATH = r"C:\HARSHITA\INTERNSHIPS\pgv\Livekitoutbboundcall-21-03-2025\livekit-outbound-caller-agent\config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

CONFIG = load_config()

def load_service(service_type, name, **kwargs):
    """
    Dynamically loads a service from the appropriate module.
    :param service_type: "llm", "tts", or "stt"
    :param name: The specific model/provider (e.g., "OpenAI", "Polly", "Transcribe")
    :return: The initialized service instance
    """
    try:
        module_path = f"services.{service_type}.{name.lower()}"
        print(f"--------ttempting to import: {module_path}----------")
        module = importlib.import_module(module_path)
        return module.load(**kwargs)  # Call the `load()` function inside the module
    except ModuleNotFoundError:
        raise ValueError(f"Invalid {service_type} selection: {name}")
    
if __name__ == "__main__":
    # Fetch selected LLM from config
    selected_tts = CONFIG["tts"]["selected_provider"]
    
    print(f"Attempting to load tts: {selected_tts}")

    try:
        tts_model = load_service("tts", selected_tts)
        print(f"✅ Successfully loaded tts: {selected_tts},{tts_model}")
    except Exception as e:
        print(f"❌ Error loading tts: {e}")