from enum import Enum
import os
import subprocess
import vosk
import sounddevice as sd
from ai_overlay import AIOverlay
from pynput import keyboard
import asyncio

class TaskInputMode(Enum):
    VOICE = "voice"
    BUTTON = "button"
    TEXT = "text"

def check_audio_config():
    """Check and optimize audio configuration for device sharing"""
    try:
        # Check if PulseAudio is running
        result = subprocess.run(['pulseaudio', '--check'], 
                              capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("PulseAudio not running, trying to start...")
            subprocess.run(['pulseaudio', '--start'], check=False)
        
        # List available audio devices
        try:
            devices = sd.query_devices()
            print(f"Available audio devices: {len(devices)} total")
            default_input = sd.query_devices(kind='input')
            print(f"Default input device: {default_input['name']} (ID: {default_input.get('index', 'N/A')})")
        except Exception as e:
            print(f"Could not query audio devices: {e}")
            return False
            
    except Exception as e:
        print(f"Audio configuration check failed: {e}")
        return False
    return True

class TaskInput:
    def __init__(self, overlay: AIOverlay):
        self.mode = TaskInputMode.BUTTON
        self.isListeningForTask = False
        self.overlay = overlay
        self.isAudioWorking = False # for testing, force text mode
        self.listener = None
        self.f13_future = None
        self.event_loop = None
        if self.isAudioWorking:
            # Initialize Vosk model
            print("Loading Vosk model...")
            if not os.path.exists("vosk-model-small"):
                print("Downloading small Vosk model...")
                subprocess.run(["wget", "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"], check=True)
                subprocess.run(["unzip", "vosk-model-small-en-us-0.15.zip"], check=True)
                subprocess.run(["mv", "vosk-model-small-en-us-0.15", "vosk-model-small"], check=True)
                subprocess.run(["rm", "vosk-model-small-en-us-0.15.zip"], check=True)

            self.model = vosk.Model("vosk-model-small")
            print("Small Vosk model loaded successfully")
        else:
            print("WARNING: Audio is not working, text mode only")
            self.mode = TaskInputMode.TEXT
            self.model = None

    def set_mode(self, mode):
        self.mode = mode

    def get_mode(self):
        return self.mode

    async def wait_for_task(self):
        if self.mode == TaskInputMode.VOICE:
            raise NotImplementedError("Voice mode not implemented")
        elif self.mode == TaskInputMode.BUTTON:
            raise NotImplementedError("Button mode not implemented")
        elif self.mode == TaskInputMode.TEXT:
            self.event_loop = asyncio.get_event_loop()
            self._f13_future = self.event_loop.create_future()
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.start()
            await self._f13_future
            self.listener.stop()
            return self.overlay.request_text_input("Enter task")

    def on_press(self, key):
        if key == keyboard.Key.f13 and self._f13_future and not self._f13_future.done():
            if self.event_loop:
                self.event_loop.call_soon_threadsafe(self._f13_future.set_result, None)
    
    def wait_for_text(self):
        return self.overlay.request_text_input("Enter task")
    
