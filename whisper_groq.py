#!/usr/bin/env python3
import argparse
import os
import requests
import json
import subprocess
import pyaudio
import wave
import tempfile
import webrtcvad
import numpy as np
from array import array
from struct import pack
import csv

def preprocess_audio(input_file, output_file, verbose=False):
    command = [
        'ffmpeg',
        '-i', input_file,
        '-ar', '16000',
        '-ac', '1',
        '-map', '0:a:',
        output_file
    ]
    if verbose:
        print(f"Running FFmpeg command: {' '.join(command)}")
    subprocess.run(command, check=True)

def transcribe_audio(file_path, api_key, model, language=None, temperature=0, task="transcribe", word_timestamps=False, initial_prompt=None, verbose=False):
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"bearer {api_key}"
    }
    data = {
        "model": model,
        "temperature": temperature,
        "response_format": "verbose_json" if word_timestamps else "json"
    }
    if language:
        data["language"] = language
    if task == "translate":
        data["task"] = "translate"
    if initial_prompt:
        data["prompt"] = initial_prompt

    if verbose:
        print(f"Sending request to Groq API:")
        print(f"  URL: {url}")
        print(f"  Headers: {headers}")
        print(f"  Data: {data}")

    with open(file_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, headers=headers, data=data, files=files)

    if response.status_code == 200:
        if verbose:
            print("Received successful response from Groq API")
        result = response.json()
        return result["text"] if not word_timestamps else result
    else:
        if verbose:
            print(f"Error response from Groq API: {response.status_code}")
            print(f"Response content: {response.text}")
        raise Exception(f"Error: {response.status_code}, {response.text}")

def record_audio_with_vad(output_file, args, silence_threshold=1.0, silence_duration=2.0):
    if args.verbose:
        print("Initializing audio recording...")
        print(f"Silence threshold: {silence_threshold}")
        print(f"Silence duration: {silence_duration}")

    CHUNK = 480  # 30ms at 16kHz
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000  # webrtcvad requires 8000, 16000, 32000, or 48000 Hz
    vad = webrtcvad.Vad(3)  # Aggressiveness mode 3 (highest)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("Recording... (Speak now, recording will stop after prolonged silence)")

    frames = []
    silent_chunks = 0
    voiced_frames = 0

    while True:
        data = stream.read(CHUNK)
        is_speech = vad.is_speech(data, RATE)
        
        if is_speech:
            frames.append(data)
            silent_chunks = 0
            voiced_frames += 1
        else:
            frames.append(data)
            silent_chunks += 1

        if voiced_frames > 0 and silent_chunks > int(silence_duration * (RATE / CHUNK)):
            break

    print("Recording finished.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Write the recorded data to a WAV file
    wf = wave.open(output_file, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    if args.verbose:
        print(f"Recording finished. Saving to {output_file}")

def save_output(transcription, output_file, format, verbose=False):
    base_name, _ = os.path.splitext(output_file)
    
    if verbose:
        print(f"Saving output in {format} format(s)")

    if format == 'txt' or format == 'all':
        txt_file = f"{base_name}.txt"
        if verbose:
            print(f"Writing to {txt_file}")
        with open(txt_file, "w") as f:
            f.write(transcription)
    
    if format == 'json' or format == 'all':
        json_file = f"{base_name}.json"
        if verbose:
            print(f"Writing to {json_file}")
        with open(json_file, "w") as f:
            json.dump({"text": transcription}, f, indent=2)
    
    if format == 'tsv' or format == 'all':
        tsv_file = f"{base_name}.tsv"
        if verbose:
            print(f"Writing to {tsv_file}")
        with open(tsv_file, "w", newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(["start", "end", "text"])
            writer.writerow(["0.00", str(len(transcription) / 20), transcription])  # Rough estimate of duration
    
    if format in ['vtt', 'srt'] or format == 'all':
        # Simple implementation for VTT and SRT (without proper timing)
        content = f"1\n00:00:00.000 --> 00:00:{len(transcription)//20:02d}.000\n{transcription}\n"
        
        if format == 'vtt' or format == 'all':
            vtt_file = f"{base_name}.vtt"
            if verbose:
                print(f"Writing to {vtt_file}")
            with open(vtt_file, "w") as f:
                f.write("WEBVTT\n\n" + content)
        
        if format == 'srt' or format == 'all':
            srt_file = f"{base_name}.srt"
            if verbose:
                print(f"Writing to {srt_file}")
            with open(srt_file, "w") as f:
                f.write(content)

def main():
    parser = argparse.ArgumentParser(description="Whisper-like CLI using Groq API")
    parser.add_argument("audio", nargs="*", help="audio file(s) to transcribe")
    parser.add_argument("--model", default="distil-whisper-large-v3-en", help="name of the Whisper model to use")
    parser.add_argument("--language", help="language spoken in the audio")
    parser.add_argument("--output_dir", "-o", default=".", help="directory to save the outputs")
    parser.add_argument("--temperature", type=float, default=0, help="temperature to use for sampling")
    parser.add_argument("--record", action="store_true", help="record audio from microphone until silence is detected")
    parser.add_argument(
        "--output_format", "-f",
        choices=["txt", "vtt", "srt", "tsv", "json", "all"],
        default="all",
        help="format of the output file; if not specified, all available formats will be produced (default: all)"
    )
    parser.add_argument("--task", choices=["transcribe", "translate"], default="transcribe",
                        help="whether to perform transcription or translation")
    parser.add_argument("--word_timestamps", action="store_true",
                        help="extract word-level timestamps (if supported by the model)")
    parser.add_argument("--initial_prompt", type=str,
                        help="optional text to provide as a prompt for the first window")
    parser.add_argument("--verbose", action="store_true",
                        help="print out progress and debug messages")

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")

    if not args.audio and not args.record:
        parser.error("Either audio file(s) or --record must be specified")

    audio_files = args.audio.copy()

    if args.record:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            record_audio_with_vad(temp_file.name, args)
            audio_files.append(temp_file.name)

    if args.verbose:
        print(f"Using model: {args.model}")
        print(f"Output directory: {args.output_dir}")
        print(f"Output format(s): {args.output_format}")
        print(f"Language: {args.language or 'Auto-detect'}")
        print(f"Temperature: {args.temperature}")
        print(f"Task: {args.task}")
        print(f"Word timestamps: {'Enabled' if args.word_timestamps else 'Disabled'}")
        print(f"Initial prompt: {args.initial_prompt or 'None'}")

    for audio_file in audio_files:
        if args.verbose:
            print(f"\nProcessing {audio_file}...")
        
        # Preprocess audio
        preprocessed_file = f"{os.path.splitext(audio_file)[0]}_preprocessed.wav"
        if args.verbose:
            print(f"Preprocessing audio: {audio_file} -> {preprocessed_file}")
        preprocess_audio(audio_file, preprocessed_file, args.verbose)

        # Transcribe
        if args.verbose:
            print(f"Transcribing {preprocessed_file}...")
        transcription = transcribe_audio(
            preprocessed_file,
            api_key,
            args.model,
            args.language,
            args.temperature,
            args.task,
            args.word_timestamps,
            args.initial_prompt,
            args.verbose
        )

        # Save output
        output_file = os.path.join(args.output_dir, os.path.basename(audio_file))
        if args.verbose:
            print(f"Saving output to: {output_file}")
        save_output(transcription, output_file, args.output_format, args.verbose)

        if args.verbose:
            print(f"Transcription saved in {args.output_format} format(s) in {args.output_dir}")

        # Clean up preprocessed file
        if args.verbose:
            print(f"Cleaning up temporary file: {preprocessed_file}")
        os.remove(preprocessed_file)

    if args.record and args.verbose:
        print(f"Removing temporary recorded file: {audio_files[-1]}")

if __name__ == "__main__":
    main()