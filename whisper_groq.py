#!/usr/bin/env python3
import argparse
import os
import tempfile
from whisper_groq_lib import record_audio_with_vad, process_audio

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
            record_audio_with_vad(temp_file.name, args.verbose)
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
        process_audio(
            audio_file,
            api_key,
            args.model,
            args.language,
            args.temperature,
            args.task,
            args.word_timestamps,
            args.initial_prompt,
            args.output_dir,
            args.output_format,
            args.verbose
        )

    if args.record and args.verbose:
        print(f"Removing temporary recorded file: {audio_files[-1]}")
        os.remove(audio_files[-1])

if __name__ == "__main__":
    main()