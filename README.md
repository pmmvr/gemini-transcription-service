# Gemini Transcription Service

A service for transcribing audio files using Google's Gemini API.

## Features

- Audio to text transcription using Gemini
- Meeting summary generation
- Local storage of transcripts and summaries
- Optional Google Cloud Storage support

## Setup

1. Clone this repository
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file using the `.env.example` as a template
4. Add your Gemini API key to the `.env` file

## Usage

### Basic Transcription

```bash
python main.py path/to/your/audio_file.mp3
```

### With Summary Generation

You can enable summary generation via command line:

```bash
python main.py path/to/your/audio_file.mp3 --summary
```

To specify a custom path for saving summaries:

```bash
python main.py path/to/your/audio_file.mp3 --summary --summary-path /custom/path/for/summaries
```

### Configuration

You can configure the service using the `.env` file:

- `GENERATE_SUMMARY=true` - Enable summary generation by default
- `SUMMARY_PATH=./summaries` - Set the default directory for saving summaries

## Output

- Transcription files are saved to the directory specified by `OUTPUT_DIR` (default: `./transcripts`)
- Summary files are saved to the directory specified by `SUMMARY_PATH` (default: `./summaries`)