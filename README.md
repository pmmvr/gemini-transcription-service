# Gemini Transcription Service

A service for transcribing audio files using Google's Gemini API with web UI.

### Try live: [gemini-transcription-service.fly.dev](https://gemini-transcription-service.fly.dev)

---

## Features

- Audio to text transcription using Gemini
- Meeting summary generation
- Local storage of transcripts and summaries
- Web interface for uploading audio and viewing transcripts
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

## Web Interface

The service includes a simple web interface for transcribing audio files:

1. Start the web server (three options):
   ```bash
   # Option 1: Simple script (recommended)
   python run.py

   # Option 2: Using Flask development server
   # First create .flaskenv with: FLASK_APP=src.gemini_transcription_service.webapp.app
   flask run

   # Option 3: Using Gunicorn (for production)
   gunicorn -c gunicorn_config.py run:app
   ```

2. Open http://localhost:5000 in your browser

3. Upload any audio file (.wav, .mp3, .m4a, .flac)

4. The interface will display:
   - The complete transcript with speaker detection
   - Options to generate and view meeting summaries
   - Buttons to download both transcripts and summaries

The web interface makes it easy to process audio files without using the command line. Configuration options are available in your `.env` file.

## Project Structure

```
gemini-transcription-service/
├── main.py                    # CLI entry point
├── run.py                     # Web interface runner
├── src/                       # Source code
│   └── gemini_transcription_service/
│       ├── config.py          # Configuration settings
│       ├── storage_handler.py # File storage utilities
│       ├── summary_generator.py # Summary generation
│       ├── transcribe.py      # Core transcription service
│       ├── transcript_processor.py # Process transcripts
│       ├── transcription_logic.py # Transcription business logic
│       └── webapp/            # Web interface
│           ├── app.py         # Flask application
│           └── templates/     # HTML templates
├── uploads/                   # Temp storage for uploads
├── transcripts/               # Output directory for transcripts
├── summaries/                 # Output directory for summaries
├── .env.example               # Example environment variables
├── .flaskenv                  # Flask configuration
├── gunicorn_config.py         # Gunicorn configuration
└── pyproject.toml             # Project dependencies and metadata
```

## Dependencies

This project uses modern Python packaging with `pyproject.toml`. The key dependencies are:

- `google-genai` - Google's Generative AI client library
- `python-dotenv` - For environment variable management
- `flask` - For the web interface
- `google-cloud-storage` - For optional GCS integration

See the `pyproject.toml` file for specific version requirements.

## Google Cloud Storage Integration (Optional)

The service can store transcripts, summaries, and audio files in Google Cloud Storage, but this is entirely optional. By default, all files are stored locally.

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

   # Google Cloud Storage Configuration for Summaries (optional)
   SUMMARY_STORAGE_ENABLED=true
   SUMMARY_BUCKET_NAME=your-gcs-bucket-name
   SUMMARY_PATH_PREFIX=summaries/

   # Google Cloud Authentication
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
   ```

2. Ensure you have valid GCP credentials and the appropriate permissions for the specified buckets.

If GCS integration is disabled (the default), all files will be stored in the local directories specified by `OUTPUT_DIR` and `SUMMARY_PATH`.

### File Naming in GCS

To prevent accidental overwrites when storing files in GCS:

- All files (transcripts, summaries, and audio) automatically include timestamps in their filenames (e.g., `meeting_summary_20240511_123045.txt`)
- Each upload generates a unique filename, even if the content is identical
- Files are organized in the GCS bucket according to the configured prefix paths
- This automatic timestamp can be disabled if needed by setting `prevent_overwrite=False` when using the StorageHandler directly
