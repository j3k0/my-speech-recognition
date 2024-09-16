from Quartz import (
    CGEventTapCreate,
    kCGHIDEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionDefault,
    CGEventTapEnable,
    CGEventTapPostEvent,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CFMachPortCreateRunLoopSource,
    CGEventGetIntegerValueField,
    CGEventGetFlags,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGKeyboardEventKeycode,
    kCGEventFlagMaskControl,
    kCGEventFlagsChanged,
    CGEventMaskBit,
    kCFRunLoopCommonModes,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand
)
import pyperclip
import threading
import os
import platform
from myspeech_lib import record_audio_with_vad, process_audio  # Updated import
import argparse  # Added import for argument parsing
import re
from pynput.keyboard import Key, Controller  # Add this import
import time  # Add this import at the top of the file


# Initialize variables for model, initial_prompt, and verbose
recording = False
stop_recording = False
control_v_pressed = False
api_key = None

model = None            # Add this line
initial_prompt = None   # Add this line
verbose = False         # Add this line
keyboard_controller = None  # Add this line

MAX_PROMPT_WORDS = 128

# Add these global variables
key_state = {'control': False, 'v': False}
last_shortcut_time = 0

retrieve_context = False  # Add this line

def hotkey_callback(proxy, event_type, event, refcon):
    global recording, stop_recording, key_state, last_shortcut_time

    key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
    flags = CGEventGetFlags(event)
    
    # Interpret the flags
    is_control_pressed = bool(flags & kCGEventFlagMaskControl)

    is_v = key_code == 9  # 'V' key code
    key_state['control'] = is_control_pressed
    if is_v:
        key_state['v'] = event_type == kCGEventKeyDown

    if key_state['control'] and key_state['v']:
        last_shortcut_time = time.time()
        if not recording:
            print("Control+V pressed. Starting recording...")
            recording = True
            stop_recording = False
            threading.Thread(target=record_and_transcribe).start()
            # record_and_transcribe()
            return None
  # elif not key_state['control'] and not key_state['v']:
  #     if recording and not stop_recording:
  #           print("Control+V released. Stopping recording...")
  #           stop_recording = True
  #           return None

    # Block events for some time after a shortcut detection
    if time.time() - last_shortcut_time < 0.3:
        if is_v:
            return None

    # Pass through all other events
    return event

def _paste_text(text):
    # Now paste the transcribed text
    global keyboard_controller
    pyperclip.copy(text)
    keyboard_controller.press(Key.cmd)
    keyboard_controller.press('v')
    keyboard_controller.release('v')
    keyboard_controller.release(Key.cmd)

def paste_text(text):
    _paste_text(text)
    
def backspace_text(text):
    # If we've exhausted all retries, return an empty string
    global keyboard_controller
    for _ in range(len(text)):
        keyboard_controller.press(Key.backspace)
        keyboard_controller.release(Key.backspace)

def get_active_text(max_retries=3):
    global keyboard_controller, verbose

    if verbose:
        print("Retrieving active text..")

    # Clear the clipboard
    keyboard_controller.type('<...>')
    pyperclip.copy('')

    for attempt in range(max_retries):
        if verbose:
            print(f"Attempt number {attempt}")
        # Select all text before the cursor
        keyboard_controller.press(Key.shift)
        keyboard_controller.press(Key.cmd)
        keyboard_controller.press(Key.up)
        keyboard_controller.release(Key.up)
        keyboard_controller.release(Key.cmd)
        keyboard_controller.release(Key.shift)
        time.sleep(0.05)
        
        # Copy the selected text
        keyboard_controller.press(Key.cmd)
        keyboard_controller.press('c')
        keyboard_controller.release('c')
        keyboard_controller.release(Key.cmd)
        time.sleep(0.05)

        # Wait for a short duration to ensure the text is copied
        result = pyperclip.paste()
        time.sleep(0.05)

        # Move cursor back to the end of "<...>"
        keyboard_controller.press(Key.right)
        keyboard_controller.release(Key.right)
        
        # Check if we got any text (excluding our marker)
        if result:
            # First, delete the "<...>" text
            if verbose:
                print(f"Text retrieved: {result}")
            backspace_text("<...>")
            time.sleep(0.05)
            return result
        else:
            print(f"Text: {result}")

        # If we didn't get any text, wait a bit before retrying
        time.sleep(0.5)

    backspace_text("<...>")

    # If we've exhausted all retries, return an empty string
    return ""

def truncate_prompt(prompt, max_words, max_chars=896):
    words = re.findall(r'\S+', prompt)
    truncated = ' '.join(words[-max_words:])
    if len(truncated) > max_chars:
        while len(truncated) > max_chars and words:
            words = words[1:]
            truncated = ' '.join(words)
    return truncated

def record_and_transcribe():
    global recording, stop_recording, verbose, retrieve_context

    try:
        active_text = ""
        if retrieve_context:
            if verbose:
                print("Getting active text")
            active_text = get_active_text()
        keyboard_controller.type("<REC>")

        the_random = os.urandom(8).hex()
        temp_audio_file = f"/tmp/audio_recording_{the_random}.wav"
        temp_text_file = f"/tmp/audio_recording_{the_random}.txt"

        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
        
        record_audio_with_vad(
            temp_audio_file,
            verbose=True, 
            silence_threshold=1.0, 
            silence_duration=1.0,
            stop_recording_callback=lambda: stop_recording
        )
        
        active_text = active_text.split("<...>")[0]

        if verbose:
            print(f"Active text: {active_text}")
        
        combined_prompt = initial_prompt or ""
        if retrieve_context:
            combined_prompt += f" {active_text}"
        
        truncated_prompt = truncate_prompt(combined_prompt, MAX_PROMPT_WORDS)

        backspace_text("<REC>")
        keyboard_controller.type("<zzz>")
        
        process_audio(
            temp_audio_file,
            api_key,
            model=model,
            language=None,
            temperature=0,
            task="transcribe",
            word_timestamps=False,
            initial_prompt=truncated_prompt,
            output_dir="/tmp",
            output_format="txt",
            verbose=verbose
        )
        
        with open(temp_text_file, "r") as f:
            text = f.read().strip()
        
        print("Transcription copied to clipboard. Pasting...")
        backspace_text("<zzz>")
        paste_text(text)
        
        print("Transcription pasted into active application.")

        # Clean up temporary files
        os.remove(temp_audio_file)
        os.remove(temp_text_file)

    except Exception as e:
        print(f"Error: {e}")
        print("Failed to record and transcribe.")
        paste_text("")
    
    recording = False

def main():
    global model, initial_prompt, verbose, keyboard_controller, api_key, retrieve_context
    parser = argparse.ArgumentParser(description="Whisper Groq Service")
    parser.add_argument("--model", default="distil-whisper-large-v3-en", help="Name of the model to use")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--initial-prompt", type=str, help="Initial prompt to include in transcription")
    parser.add_argument("--retrieve-context", action="store_true", help="Retrieve context from active text box")  # Add this line
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")

    verbose = args.verbose
    model = args.model
    initial_prompt = args.initial_prompt
    retrieve_context = args.retrieve_context  # Add this line
    keyboard_controller = Controller()  # Initialize keyboard_controller here

    print("Whisper Groq Service is running.")
    print("Press Control+V to start/stop recording.")

    event_mask = CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp) | CGEventMaskBit(kCGEventFlagsChanged)

    tap = CGEventTapCreate(
        kCGHIDEventTap,
        kCGHeadInsertEventTap,
        kCGEventTapOptionDefault,
        event_mask,
        hotkey_callback,
        None
    )

    if not tap:
        print("Failed to create event tap.")
        exit(1)

    run_loop_source = CFMachPortCreateRunLoopSource(None, tap, 0)
    CFRunLoopAddSource(CFRunLoopGetCurrent(), run_loop_source, kCFRunLoopCommonModes)
    CGEventTapEnable(tap, True)
    CFRunLoopRun()

if __name__ == "__main__":
    main()
