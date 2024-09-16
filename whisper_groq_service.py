import os
import threading
import pyperclip
from pynput import keyboard
import platform
from whisper_groq_lib import record_audio_with_vad, process_audio

recording = False
stop_recording = False
is_mac = platform.system() == 'Darwin'

def on_activate_v():
    global recording, stop_recording
    if not recording:
        print("Shortcut Control+V pressed. Starting recording...")
        recording = True
        stop_recording = False
        threading.Thread(target=record_and_transcribe).start()
    else:
        print("Shortcut Control+V pressed again. Stopping recording...")
        stop_recording = True

def on_activate_q():
    print("Shortcut Control+Q pressed. Exiting...")
    return False  # Stop the listener

def paste_text():
    keyboard_controller = keyboard.Controller()
    with keyboard_controller.pressed(keyboard.Key.cmd if is_mac else keyboard.Key.ctrl):
        keyboard_controller.press('v')
        keyboard_controller.release('v')

def record_and_transcribe():
    global recording, stop_recording
    
    temp_file = "/tmp/audio_recording.wav"
    
    record_audio_with_vad(
        temp_file,
        verbose=True, 
        silence_threshold=1.0, 
        silence_duration=2.0,
        stop_recording_callback=lambda: stop_recording
    )
    
    recording = False
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY environment variable is not set")
        return

    try:
        process_audio(
            temp_file,
            api_key,
            model="distil-whisper-large-v3-en",
            language=None,
            temperature=0,
            task="transcribe",
            word_timestamps=False,
            initial_prompt=None,
            output_dir="/tmp",
            output_format="txt",
            verbose=True
        )
        
        with open("/tmp/audio_recording.txt", "r") as f:
            text = f.read().strip()
        
        pyperclip.copy(text)
        
        print("Transcription copied to clipboard. Pasting...")
        paste_text()
        
        print("Transcription pasted into active application.")
    except Exception as e:
        print(f"Error during transcription: {e}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists("/tmp/audio_recording.txt"):
            os.remove("/tmp/audio_recording.txt")

def main():
    print("Whisper Groq Service is running.")
    print("Press Control+V to start/stop recording.")
    print("Press Control+Q to quit the application.")

    with keyboard.GlobalHotKeys({
            '<ctrl>+v': on_activate_v,
            '<ctrl>+q': on_activate_q
    }) as h:
        h.join()

if __name__ == "__main__":
    main()
