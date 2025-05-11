# Gemini Transcription Service

A service for transcribing audio files using Google's Gemini API.

## Features

- Audio to text transcription using Gemini
- Meeting summary generation
- Local storage of transcripts and summaries
- Optional Google Cloud Storage integration (disabled by default)

## Setup

1. Clone this repository
2. Install the project and its dependencies:
   ```bash
   # Install in development mode
   pip install -e .

   # Or for regular installation
   pip install .
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

## Project Structure

```
gemini-transcription-service/
├── main.py                    # CLI entry point
├── src/                       # Source code
│   └── gemini_transcription_service/
│       ├── config.py          # Configuration settings
│       ├── storage_handler.py # File storage utilities
│       ├── summary_generator.py # Summary generation
│       ├── transcribe.py      # Core transcription service
│       ├── transcript_processor.py # Process transcripts
│       └── transcription_logic.py # Transcription business logic
├── uploads/                   # Temp storage for uploads
├── transcripts/               # Output directory for transcripts
├── summaries/                 # Output directory for summaries
├── .env.example               # Example environment variables
└── pyproject.toml             # Project dependencies and metadata
```

## Dependencies

This project uses modern Python packaging with `pyproject.toml`. The key dependencies are:

- `google-genai` - Google's Generative AI client library
- `python-dotenv` - For environment variable management
- `google-cloud-storage` - For optional GCS integration

See the `pyproject.toml` file for specific version requirements.

## Google Cloud Storage Integration (Optional)

The service can store transcripts and audio files in Google Cloud Storage, but this is entirely optional. By default, all files are stored locally.

To enable GCS integration:

1. Set the following environment variables in your `.env` file:
   ```
   # Google Cloud Storage Configuration for Transcripts
   TRANSCRIPT_STORAGE_ENABLED=true
   TRANSCRIPT_BUCKET_NAME=your-gcs-bucket-name
   TRANSCRIPT_PATH_PREFIX=transcripts/

   # Google Cloud Storage Configuration for Audio Files (optional)
   AUDIO_STORAGE_ENABLED=true
   AUDIO_BUCKET_NAME=your-audio-bucket-name
   AUDIO_PATH_PREFIX=audio/

   # Google Cloud Authentication
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
   ```

2. Ensure you have valid GCP credentials and the appropriate permissions for the specified buckets.

If GCS integration is disabled (the default), all files will be stored in the local directories specified by `OUTPUT_DIR` and `SUMMARY_PATH`.