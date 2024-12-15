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
import math

# Add these constants at the top of the file
MAX_SEGMENT_DURATION = 10  # Maximum duration in seconds for each audio segment
MIN_SILENCE_DURATION = 0.5  # Minimum silence duration to consider for splitting
DEFAULT_SILENCE_DURATION = 2.0  # Default silence duration before auto-stopping

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

    if not verbose:
        # Add flags to suppress FFmpeg output unless verbose is True
        command.insert(1, '-hide_banner')  # Hide FFmpeg compilation details
        command.insert(2, '-loglevel')
        command.insert(3, 'error')         # Only show errors
    
    if verbose:
        print(f"Running FFmpeg command: {' '.join(command)}")
    
    subprocess.run(command, check=True, capture_output=not verbose)

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

def split_audio_at_silence(frames, chunk_size, channels, sample_width, rate, vad, verbose=False):
    """Split audio into segments at silence points"""
    segments = []
    current_segment = []
    silent_chunks = 0
    total_chunks = len(frames)
    
    for i, chunk in enumerate(frames):
        is_speech = vad.is_speech(chunk, rate)
        
        if is_speech:
            silent_chunks = 0
        else:
            silent_chunks += 1
        
        current_segment.append(chunk)
        
        # Calculate current segment duration
        segment_duration = len(current_segment) * chunk_size / rate
        
        # Check if we need to split (either max duration reached or long silence detected)
        if (segment_duration >= MAX_SEGMENT_DURATION and silent_chunks >= int(MIN_SILENCE_DURATION * (rate / chunk_size))) or \
           (i == total_chunks - 1 and current_segment):
            
            if verbose:
                print(f"Creating segment of {segment_duration:.2f} seconds")
            
            segments.append(current_segment)
            current_segment = []
            silent_chunks = 0
    
    # Add any remaining frames as the last segment
    if current_segment:
        segments.append(current_segment)
    
    return segments

def save_audio_segment(frames, filename, channels, sample_width, rate):
    """Save a segment of audio frames to a WAV file"""
    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(sample_width)
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

def record_audio_with_vad(output_file, verbose=False, silence_threshold=1.0, silence_duration=DEFAULT_SILENCE_DURATION, stop_recording_callback=None):
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

    try:
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

            # Stop if silence duration exceeded
            if voiced_frames > 0 and silent_chunks > int(silence_duration * (RATE / CHUNK)):
                break

        print("Recording finished.")
        
        # Split audio into segments if needed
        segments = split_audio_at_silence(frames, CHUNK, CHANNELS, p.get_sample_size(FORMAT), RATE, vad, verbose)
        
        if len(segments) == 1:
            # If only one segment, save directly to output file
            save_audio_segment(segments[0], output_file, CHANNELS, p.get_sample_size(FORMAT), RATE)
            return [output_file]
        else:
            # Save multiple segments
            segment_files = []
            for i, segment in enumerate(segments):
                segment_file = f"{os.path.splitext(output_file)[0]}_segment_{i}.wav"
                save_audio_segment(segment, segment_file, CHANNELS, p.get_sample_size(FORMAT), RATE)
                segment_files.append(segment_file)
            return segment_files

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

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