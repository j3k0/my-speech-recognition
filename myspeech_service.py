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
    kCGEventFlagMaskCommand,
    CGEventCreateKeyboardEvent,
    CGEventSetFlags,
    CGEventPost
)
import threading
import os
import platform
from myspeech_lib import record_audio_with_vad, process_audio
import argparse
import re
import time
from AppKit import NSPasteboard, NSStringPboardType
import logging
from contextlib import contextmanager

class MacOSKeyboardController:
    def __init__(self):
        self.key_map = {
            'a': 0x00, 'b': 0x0B, 'c': 0x08, 'd': 0x02, 'e': 0x0E, 'f': 0x03, 'g': 0x05,
            'h': 0x04, 'i': 0x22, 'j': 0x26, 'k': 0x28, 'l': 0x25, 'm': 0x2E, 'n': 0x2D,
            'o': 0x1F, 'p': 0x23, 'q': 0x0C, 'r': 0x0F, 's': 0x01, 't': 0x11, 'u': 0x20,
            'v': 0x09, 'w': 0x0D, 'x': 0x07, 'y': 0x10, 'z': 0x06,
            '1': 0x12, '2': 0x13, '3': 0x14, '4': 0x15, '5': 0x17, '6': 0x16, '7': 0x1A,
            '8': 0x1C, '9': 0x19, '0': 0x1D,
            '\n': 0x24, '\t': 0x30, ' ': 0x31, '-': 0x1B, '=': 0x18, '[': 0x21, ']': 0x1E,
            '\\': 0x2A, ';': 0x29, "'": 0x27, ',': 0x2B, '.': 0x2F, '/': 0x2C,
            'left': 0x7B, 'right': 0x7C, 'up': 0x7E, 'down': 0x7D,
            'backspace': 0x33, 'delete': 0x75, 'cmd': 0x37, 'shift': 0x38, 'caps': 0x39,
            'option': 0x3A, 'ctrl': 0x3B, 'esc': 0x35,
            'f1': 0x7A, 'f2': 0x78, 'f3': 0x63, 'f4': 0x76,
            'f5': 0x60, 'f6': 0x61, 'f7': 0x62, 'f8': 0x64,
            'f9': 0x65, 'f10': 0x6D, 'f11': 0x67, 'f12': 0x6F,
            'home': 0x73, 'end': 0x77, 'pageup': 0x74, 'pagedown': 0x79,
            'return': 0x24, 'enter': 0x4C, 'tab': 0x30,
            'space': 0x31, 'capslock': 0x39,
            'numlock': 0x47, 'function': 0x3F,
        }
        self.modifier_keys = {
            'cmd': 0x100000,
            'command': 0x100000, # alias for cmd
            'shift': 0x20000,
            'option': 0x80000,
            'ctrl': 0x40000,
            'capslock': 0x10000,
            'fn': 0x800000,
        }
        self.logger = logging.getLogger(__name__)

    def press_key(self, key, modifiers=None):
        try:
            key_code = self.key_map.get(key.lower())
            if key_code is not None:
                event = CGEventCreateKeyboardEvent(None, key_code, True)
                if modifiers:
                    flags = 0
                    for mod in modifiers:
                        flags |= self.modifier_keys.get(mod.lower(), 0)
                    CGEventSetFlags(event, flags)
                CGEventPost(kCGHIDEventTap, event)
        except Exception as e:
            self.logger.error(f"Error pressing key {key}: {str(e)}")

    def release_key(self, key, modifiers=None):
        try:
            key_code = self.key_map.get(key.lower())
            if key_code is not None:
                event = CGEventCreateKeyboardEvent(None, key_code, False)
                if modifiers:
                    flags = 0
                    for mod in modifiers:
                        flags |= self.modifier_keys.get(mod.lower(), 0)
                    CGEventSetFlags(event, flags)
                CGEventPost(kCGHIDEventTap, event)
        except Exception as e:
            self.logger.error(f"Error releasing key {key}: {str(e)}")

    def type_with_modifiers(self, key, modifiers):
        self.press_key(key, modifiers)
        time.sleep(0.01)
        self.release_key(key, modifiers)

    def type_special_char(self, char):
        special_chars = {
            '@': ('shift', '2'),
            '#': ('shift', '3'),
            '$': ('shift', '4'),
            '%': ('shift', '5'),
            '^': ('shift', '6'),
            '&': ('shift', '7'),
            '*': ('shift', '8'),
            '(': ('shift', '9'),
            ')': ('shift', '0'),
            '_': ('shift', '-'),
            '+': ('shift', '='),
            '{': ('shift', '['),
            '}': ('shift', ']'),
            '|': ('shift', '\\'),
            ':': ('shift', ';'),
            '"': ('shift', "'"),
            '<': ('shift', ','),
            '>': ('shift', '.'),
            '?': ('shift', '/'),
            '~': ('shift', '`'),
        }
        if char in special_chars:
            self.type_with_modifiers(special_chars[char][1], [special_chars[char][0]])
        else:
            self.press_and_release(char)

    def type_string(self, string):
        for char in string:
            if char.isalnum() or char in [' ', '\n', '\t']:
                if char.isupper():
                    self.type_with_modifiers(char.lower(), ['shift'])
                else:
                    self.press_and_release(char)  # Ensure lowercase
            else:
                self.type_special_char(char)
            time.sleep(0.01)  # Small delay between keystrokes

    def press_and_release(self, key, modifiers=None):
        self.press_key(key, modifiers)
        # time.sleep(0.01)
        self.release_key(key, modifiers)

    def key_combination(self, *keys):
        modifiers = [key for key in keys if key in self.modifier_keys]
        regular_keys = [key for key in keys if key not in self.modifier_keys]
        for key in regular_keys:
            self.press_key(key, modifiers)
        for key in reversed(regular_keys):
            self.release_key(key, modifiers)

    @contextmanager
    def hold_keys(self, *keys):
        for key in keys:
            self.press_key(key)
        try:
            yield
        finally:
            for key in reversed(keys):
                self.release_key(key)

# Initialize global variables
recording = False
stop_recording = False
control_v_pressed = False
api_key = None
model = None
initial_prompt = None
verbose = False
keyboard_controller = MacOSKeyboardController()  # Initialize at the top level

MAX_PROMPT_WORDS = 128

key_state = {'control': False, 'v': False}
last_shortcut_time = 0

retrieve_context = False

def hotkey_callback(proxy, event_type, event, refcon):
    global recording, stop_recording, last_shortcut_time

    key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
    flags = CGEventGetFlags(event)
    
    is_control_pressed = bool(flags & kCGEventFlagMaskControl)
    is_v_pressed = key_code == 9 and event_type == kCGEventKeyDown

    if is_control_pressed and is_v_pressed:
        last_shortcut_time = time.time()
        if not recording:
            print("Control+V pressed. Starting recording...")
            recording = True
            stop_recording = False
            threading.Thread(target=record_and_transcribe).start()
            return None

    # Block events for some time after a shortcut detection
    if time.time() - last_shortcut_time < 0.3:
        if key_code == 9:  # 'V' key
            return None

    return event

def _paste_text(text, verbose):
    global keyboard_controller
    copy_to_clipboard(text)
    if verbose:
        print(f"\"{text}\" copied to clipboard.")
        print("pasting...")
    keyboard_controller.key_combination('cmd', 'v')
    time.sleep(0.1)  # Give some time for the paste operation to complete
    if verbose:
        print("Transcription pasted into active application.")

def paste_text(text, verbose):
    _paste_text(text, verbose)
    
def backspace_text(text):
    global keyboard_controller
    for _ in range(len(text)):
        keyboard_controller.press_and_release('backspace')

def get_active_text(max_retries=3):
    global keyboard_controller, verbose

    if verbose:
        print("Retrieving active text..")

    # Clear the clipboard
    keyboard_controller.type_string('<...>')
    copy_to_clipboard('')

    for attempt in range(max_retries):
        if verbose:
            print(f"Attempt number {attempt}")
        # Select all text before the cursor
        with keyboard_controller.hold_keys('shift', 'cmd'):
            keyboard_controller.press_and_release('up')
        time.sleep(0.05)
        
        # Copy the selected text
        keyboard_controller.key_combination('cmd', 'c')
        time.sleep(0.05)

        # Wait for a short duration to ensure the text is copied
        result = paste_from_clipboard()
        time.sleep(0.05)

        # Move cursor back to the end of "<...>"
        keyboard_controller.press_and_release('right')
        
        # Check if we got any text (excluding our marker)
        if result:
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
    global recording, stop_recording, verbose, retrieve_context, keyboard_controller
    
    original_clipboard_content = paste_from_clipboard()

    try:
        active_text = get_active_text() if retrieve_context else ""
        keyboard_controller.type_string("<REC>")

        the_random = os.urandom(8).hex()
        temp_audio_file = f"/tmp/audio_recording_{the_random}.wav"
        temp_text_file = f"/tmp/audio_recording_{the_random}.txt"

        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
        
        record_audio_with_vad(
            temp_audio_file,
            verbose=verbose, 
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
        keyboard_controller.type_string("<zzz>")
        
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
        
        if verbose:
            print("Transcription:")
            print(text)
            print()

        backspace_text("<zzz>")
        paste_text(text, verbose)

        # Clean up temporary files
        os.remove(temp_audio_file)
        os.remove(temp_text_file)

    except Exception as e:
        print(f"Error: {e}")
        print("Failed to record and transcribe.")
        paste_text("")

    finally:
        recording = False
        if verbose:
            print(f"Restoring original clipboard content: {original_clipboard_content}")
        time.sleep(0.5)
        copy_to_clipboard(original_clipboard_content)

def copy_to_clipboard(text):
    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setString_forType_(text, NSStringPboardType)

def paste_from_clipboard():
    pasteboard = NSPasteboard.generalPasteboard()
    return pasteboard.stringForType_(NSStringPboardType)

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
    keyboard_controller = MacOSKeyboardController()  # Initialize keyboard_controller here

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
