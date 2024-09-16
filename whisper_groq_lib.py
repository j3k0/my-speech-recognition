import os
import requests
import json
import subprocess
import pyaudio
import wave
import webrtcvad
import numpy as np
from array import array
from struct import pack
import csv

def preprocess_audio(input_file, output_file, verbose=False):
    # Remove the output file if it exists
    if os.path.exists(output_file):
        os.remove(output_file)
        if verbose:
            print(f"Removed existing output file: {output_file}")
    command = [
        'ffmpeg',
        '-i', input_file,
        '-ar', '16000',
        '-ac', '1',
        '-map', '0:a:',
        '-b:a', '32k',  # Reduce bitrate to 32 kbps
        '-acodec', 'libmp3lame',  # Use MP3 codec for good compression and compatibility
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

def record_audio_with_vad(output_file, verbose=False, silence_threshold=1.0, silence_duration=2.0, stop_recording_callback=None):
    if verbose:
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
        if stop_recording_callback and stop_recording_callback():
            break

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

    if verbose:
        print(f"Recording finished. Saving to {output_file}")

    # Write the recorded data to a WAV file
    wf = wave.open(output_file, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

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

def process_audio(audio_file, api_key, model, language, temperature, task, word_timestamps, initial_prompt, output_dir, output_format, verbose=False):
    if verbose:
        print(f"\nProcessing {audio_file}...")
    
    # Preprocess audio
    preprocessed_file = f"{os.path.splitext(audio_file)[0]}_preprocessed.mp3"
    if verbose:
        print(f"Preprocessing audio: {audio_file} -> {preprocessed_file}")
    preprocess_audio(audio_file, preprocessed_file, verbose)

    # Transcribe
    if verbose:
        print(f"Transcribing {preprocessed_file}...")
    transcription = transcribe_audio(
        preprocessed_file,
        api_key,
        model,
        language,
        temperature,
        task,
        word_timestamps,
        initial_prompt,
        verbose
    )

    # Save output
    output_file = os.path.join(output_dir, os.path.basename(audio_file))
    if verbose:
        print(f"Saving output to: {output_file}")
    save_output(transcription, output_file, output_format, verbose)

    if verbose:
        print(f"Transcription saved in {output_format} format(s) in {output_dir}")

    # Clean up preprocessed file
    if verbose:
        print(f"Cleaning up temporary file: {preprocessed_file}")
    os.remove(preprocessed_file)

    return output_file