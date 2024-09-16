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

recording = False
stop_recording = False
control_v_pressed = False  # New variable to track if Control+V is pressed

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
