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
    CGEventMaskBit,
    kCFRunLoopCommonModes
)
import pyperclip
import threading
import os
import platform
from whisper_groq_lib import record_audio_with_vad, process_audio
import argparse  # Added import for argument parsing
import re
from pynput.keyboard import Key, Controller  # Add this import

# Initialize variables for model, initial_prompt, and verbose
recording = False
stop_recording = False
control_v_pressed = False

model = None            # Add this line
initial_prompt = None   # Add this line
verbose = False         # Add this line
keyboard_controller = None  # Add this line

MAX_PROMPT_WORDS = 128

def hotkey_callback(proxy, event_type, event, refcon):
    global recording, stop_recording, control_v_pressed

    key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
    flags = CGEventGetFlags(event)

    is_control_v = key_code == 9 and (flags & kCGEventFlagMaskControl)

    if is_control_v:
        if event_type == kCGEventKeyDown and not control_v_pressed:
            control_v_pressed = True
            if not recording:
                print("Control+V pressed. Starting recording...")
                recording = True
                stop_recording = False
                threading.Thread(target=record_and_transcribe).start()
            # Suppress the event
            return None

        elif event_type == kCGEventKeyUp and control_v_pressed:
            control_v_pressed = False
            if recording:
                print("Control+V released. Stopping recording...")
                stop_recording = True
            # Suppress the event
            return None
        return None

    # Allow other events
    return event

def paste_text():
    from pynput.keyboard import Key, Controller
    keyboard_controller = Controller()
    keyboard_controller.press(Key.cmd)
    keyboard_controller.press('v')
    keyboard_controller.release('v')
    keyboard_controller.release(Key.cmd)

def get_active_text():
    # Copy text from active textbox
    keyboard_controller.press(Key.cmd)
    keyboard_controller.press('a')
    keyboard_controller.release('a')
    keyboard_controller.release(Key.cmd)
    
    keyboard_controller.press(Key.cmd)
    keyboard_controller.press('c')
    keyboard_controller.release('c')
    keyboard_controller.release(Key.cmd)

    # Unselect the text and return to the original cursor position
    keyboard_controller.press(Key.left)
    keyboard_controller.release(Key.left)
    keyboard_controller.press(Key.right)
    keyboard_controller.release(Key.right)
    
    return pyperclip.paste()

def truncate_prompt(prompt, max_words):
    words = re.findall(r'\S+', prompt)
    if len(words) > max_words:
        return ' '.join(words[:max_words])
    return prompt

def record_and_transcribe():
    global recording, stop_recording, model, initial_prompt, verbose
    
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
        # Get text from active textbox
        active_text = get_active_text()

        # Display active text in verbose mode
        if verbose:
            print(f"Active text: {active_text}")
        
        # Combine initial prompt with active text
        combined_prompt = f"{initial_prompt or ''} {active_text}".strip()
        
        # Truncate the combined prompt
        truncated_prompt = truncate_prompt(combined_prompt, MAX_PROMPT_WORDS)
        
        process_audio(
            temp_file,
            api_key,
            model=model,                     # Use specified model
            language=None,
            temperature=0,
            task="transcribe",
            word_timestamps=False,
            initial_prompt=truncated_prompt,   # Use the truncated prompt
            output_dir="/tmp",
            output_format="txt",
            verbose=verbose                  # Use specified verbosity
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
    global model, initial_prompt, verbose, keyboard_controller  # Add keyboard_controller
    parser = argparse.ArgumentParser(description="Whisper Groq Service")
    parser.add_argument("--model", default="distil-whisper-large-v3-en", help="Name of the model to use")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--initial-prompt", type=str, help="Initial prompt to include in transcription")
    args = parser.parse_args()

    verbose = args.verbose
    model = args.model
    initial_prompt = args.initial_prompt
    keyboard_controller = Controller()  # Initialize keyboard_controller here

    print("Whisper Groq Service is running.")
    print("Press Control+V to start/stop recording.")

    event_mask = CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp)

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
