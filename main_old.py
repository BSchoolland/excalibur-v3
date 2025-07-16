import json
from agent_core import Agent
import asyncio
import pygame
import sys
import os
import warnings
import subprocess
import sounddevice as sd
import vosk
import queue
import threading
import signal
import atexit
from pynput import keyboard

USE_ACTIVATION_WORD = False
ACTIVATION_WORD = "excalibur"

# Initialize Vosk model
print("Loading Vosk model...")
if not os.path.exists("vosk-model-small"):
    print("Downloading small Vosk model...")
    subprocess.run(["wget", "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"], check=True)
    subprocess.run(["unzip", "vosk-model-small-en-us-0.15.zip"], check=True)
    subprocess.run(["mv", "vosk-model-small-en-us-0.15", "vosk-model-small"], check=True)
    subprocess.run(["rm", "vosk-model-small-en-us-0.15.zip"], check=True)

model = vosk.Model("vosk-model-small")
print("Small Vosk model loaded successfully")

listening_for_task = False

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
            
    except Exception as e:
        print(f"Audio configuration check failed: {e}")

# Send a system notification using notify-send
def send_notification(title, message):
    """Send a system notification using notify-send (Linux)"""
    subprocess.run(['notify-send', title, message], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

def record_and_transcribe():
    send_notification("Excalibur Agent", "Listening for task")
    # return "Take a look at my screen and tell me what you see by using the show_info_to_user tool."
    q = queue.Queue()
    samplerate = 16000

    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    rec = vosk.KaldiRecognizer(model, samplerate)
    print("Recording... Speak now.")
    with sd.RawInputStream(samplerate=samplerate, blocksize = 8000, dtype='int16',
                           channels=1, callback=callback):
        silence_count = 0
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = rec.Result()
                break
            # Check for silence (no speech detected for a while)
            res = json.loads(rec.PartialResult())
            if not res.get("partial"):
                silence_count += 1
            else:
                silence_count = 0
            if silence_count > 20:  # ~2 seconds of silence
                result = rec.FinalResult()
                break
        print("Transcription result:")
        print(result)
        # {"text" : "test"}
        
        result_json = json.loads(result)
        return result_json["text"]
    
async def wait_for_activation_word(): 
    rec = vosk.KaldiRecognizer(model, 16000)
    rec.SetWords(True)
    q = queue.Queue()

    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype='int16',
                           channels=1, callback=callback):
        while True:
            try:
                data = q.get(timeout=1)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        print(f"Heard: {text}")
                        current_text = text.lower()
                        words = current_text.split()
                        if words and ACTIVATION_WORD in words:
                            print(f"Activation word detected in phrase: {current_text}")
                            return
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing audio: {e}")

async def task_loop():
    global USE_ACTIVATION_WORD
    loop = asyncio.get_event_loop()
    key_pressed = asyncio.Event()
    mode_changed = asyncio.Event()
    last_f13_time = 0
    double_tap_threshold = 0.3 # in seconds

    def on_press(key):
        nonlocal last_f13_time
        global USE_ACTIVATION_WORD
        try:
            if key == keyboard.Key.f13:
                import time
                current_time = time.time()
                if current_time - last_f13_time < double_tap_threshold:
                    # Double tap detected - toggle mode
                    USE_ACTIVATION_WORD = not USE_ACTIVATION_WORD
                    mode = "voice activation" if USE_ACTIVATION_WORD else "press-to-talk"
                    send_notification("Excalibur Agent", f"Switched to {mode} mode")
                    print(f"Mode switched to: {mode}")
                    loop.call_soon_threadsafe(mode_changed.set)
                else:
                    # Single tap - delay to check for potential double tap
                    def delayed_trigger():
                        import time
                        # Check if mode is still press-to-talk and no double tap occurred
                        if not USE_ACTIVATION_WORD and time.time() - current_time > double_tap_threshold:
                            loop.call_soon_threadsafe(key_pressed.set)
                    
                    if not USE_ACTIVATION_WORD:
                        timer = threading.Timer(double_tap_threshold + 0.1, delayed_trigger)
                        timer.start()
                last_f13_time = current_time
        except AttributeError:
            pass

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    skip_start_notif = False
    while True:
        if USE_ACTIVATION_WORD:
            if not skip_start_notif:
                send_notification("Excalibur Agent", "Listening for activation word")
                skip_start_notif = True
            # Wait for either activation word or mode change
            activation_task = asyncio.create_task(wait_for_activation_word())
            mode_task = asyncio.create_task(mode_changed.wait())
            
            done, pending = await asyncio.wait([activation_task, mode_task], return_when=asyncio.FIRST_COMPLETED)
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            if mode_task in done:
                # Mode was changed, restart loop
                mode_changed.clear()
                continue
            else:
                # Activation word detected
                task = record_and_transcribe()
                print('task:', task)
        else:
            if not skip_start_notif:
                send_notification("Excalibur Agent", "Press F13 to activate (or double-tap to toggle mode)")
                skip_start_notif = True
            # Wait for either key press or mode change
            key_task = asyncio.create_task(key_pressed.wait())
            mode_task = asyncio.create_task(mode_changed.wait())
            
            done, pending = await asyncio.wait([key_task, mode_task], return_when=asyncio.FIRST_COMPLETED)
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            if mode_task in done:
                # Mode was changed, restart loop
                mode_changed.clear()
                continue
            else:
                # Key was pressed
                print("F13 key pressed")
                key_pressed.clear()
                task = record_and_transcribe()
                print('task:', task)
        if task == "" or task == "huh":
            send_notification("Excalibur Agent", "No task detected")
            skip_start_notif = True
            continue
        agent = await Agent.create(
            model='gpt-4.1',
            mcp_servers=['wrapper.py', {'command': 'node', 'args': ['playwright-mcp/cli.js', '--isolated', '--headless']}],
            type='simple',
            system_prompt="You are going to be given an audio transcription of a user's goal.  You will perform only that task, and do nothing else.  It is possible that the audio transcription is not clear, in such cases make your best guess as to the goal.  If the transcription cannot be understood, then return the task as failed.  If the user asks for information, you should always call the show_info_to_user tool before marking the task as complete."
        )
        send_notification("Excalibur Agent", "Performing task: " + task)
        result = await agent.run("Audio transcription of user's goal: " + task)
        print(result)
        if result["state"] == "success":
            send_notification("Excalibur Agent", "Done!")
            skip_start_notif = True
        else:
            send_notification("Excalibur Agent", "Failed to complete task: " + result["error"])
            skip_start_notif = True
        await agent.close()
        await asyncio.sleep(0.1)

def main():
    check_audio_config()
    asyncio.run(task_loop())

if __name__ == "__main__":
    main()
