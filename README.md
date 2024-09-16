# My Speech Recognition for macOS

An easy-to-use macOS application **and command-line tool** that integrates with Groq's API for speech recognition. Simply press a shortcut key, start speaking, release it, and the transcribed text will be pasted directly into your active application.

## Features

- **Seamless Integration**: Works with any macOS application that accepts text input.
- **Shortcut Activation**: Use a keyboard shortcut to start and stop recording.
- **Real-Time Transcription**: Utilizes Groq's Whisper models for fast and accurate speech-to-text conversion.
- **Contextual Awareness**: Optionally retrieve context from the active text box to improve transcription accuracy.
- **Customizable**: Adjust settings like model selection, verbosity, and initial prompts.
- **Command-Line Interface**: Transcribe audio files or record from the microphone directly via CLI.

## Requirements

- **Operating System**: macOS
- **Python**: 3.7 or higher
- **Dependencies**:
  - `pyaudio`
  - `webrtcvad`
  - `pyobjc`
  - `pyperclip`
  - `pynput`
  - `requests`
  - `numpy`
- **Additional Tools**:
  - **FFmpeg**: Install separately.
- **Groq API Key**: Obtain from Groq.

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/j3k0/my-speech-recognition.git
   cd my-speech-recognition
   ```

2. **Set Up Virtual Environment** *(Optional but recommended)*:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**:

   Install via Homebrew:

   ```bash
   brew install ffmpeg
   ```

5. **Set the Groq API Key**:

   Export your API key as an environment variable:

   ```bash
   export GROQ_API_KEY='your_api_key_here'
   ```

   *Alternatively, you can add your API key to a `.env` file.*

## Usage

### macOS Application

Run the main service script:

```bash
python whisper_groq_service.py
```

This will start the application in the background. Press **Control+V** to start recording; release to stop recording. The transcribed text will be pasted into your active application.

**Available Options** for `whisper_groq_service.py`:

```text
usage: whisper_groq_service.py [-h] [--model MODEL] [--verbose] [--initial-prompt INITIAL_PROMPT] [--retrieve-context]

Optional arguments:
   -h, --help show this help message and exit
   --model MODEL Name of the model to use
   --verbose Enable verbose output
   --initial-prompt INITIAL_PROMPT Initial prompt to include in transcription
   --retrieve-context Retrieve context from active text box
```

#### Examples

- **Run with Default Settings:**

  ```bash
  python whisper_groq_service.py
  ```

- **Specify a Different Model and Enable Verbose Output:**

  ```bash
  python whisper_groq_service.py --model distil-whisper-large-v3-en --verbose
  ```

- **Use an Initial Prompt:**

  ```bash
  python whisper_groq_service.py --initial-prompt "The meeting notes are as follows:"
  ```

- **Retrieve Context from Active Text Box:**

  ```bash
  python whisper_groq_service.py --retrieve-context
  ```

### Command-Line Interface (CLI) Tool

You can also use the CLI tool to transcribe audio files or record from the microphone.

#### Transcribe Audio Files

```bash
python whisper_groq.py audio1.wav audio2.mp3
```

#### Record from Microphone

Record and transcribe audio from your microphone:

```bash
python whisper_groq.py --record
```

#### Available Options

```text
usage: whisper_groq.py [-h] [--model MODEL] [--language LANGUAGE]
                       [--output_dir OUTPUT_DIR] [--temperature TEMPERATURE]
                       [--record]
                       [--output_format {txt,vtt,srt,tsv,json,all}]
                       [--task {transcribe,translate}] [--word_timestamps]
                       [--initial_prompt INITIAL_PROMPT] [--verbose]
                       [audio [audio ...]]

Whisper-like CLI using Groq API

positional arguments:
  audio                 audio file(s) to transcribe

optional arguments:
  -h, --help            show this help message and exit
  --model MODEL         name of the Whisper model to use
  --language LANGUAGE   language spoken in the audio
  --output_dir OUTPUT_DIR, -o OUTPUT_DIR
                        directory to save the outputs
  --temperature TEMPERATURE
                        temperature to use for sampling
  --record              record audio from microphone until silence is detected
  --output_format {txt,vtt,srt,tsv,json,all}, -f {txt,vtt,srt,tsv,json,all}
                        format of the output file; default is 'all'
  --task {transcribe,translate}
                        perform transcription or translation
  --word_timestamps     extract word-level timestamps
  --initial_prompt INITIAL_PROMPT
                        initial prompt for the first window
  --verbose             print progress and debug messages
```

#### Examples

- **Transcribe Multiple Audio Files:**

  ```bash
  python whisper_groq.py audio1.wav audio2.mp3
  ```

- **Record and Transcribe from Microphone:**

  ```bash
  python whisper_groq.py --record
  ```

- **Specify a Different Model:**

  ```bash
  python whisper_groq.py --model distil-whisper-large-v3-en audio.wav
  ```

- **Set Language:**

  ```bash
  python whisper_groq.py --language en audio.wav
  ```

- **Choose Output Directory and Format:**

  ```bash
  python whisper_groq.py -o transcripts/ -f txt audio.wav
  ```

- **Translate Audio to English:**

  ```bash
  python whisper_groq.py --task translate audio.wav
  ```

- **Enable Verbose Output:**

  ```bash
  python whisper_groq.py --verbose audio.wav
  ```

## License

[MIT License](LICENSE)