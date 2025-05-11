from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
import os
import uuid
import json
from werkzeug.utils import secure_filename

# Try both relative and absolute imports to work in different contexts
try:
    from ..transcribe import TranscriptionService
    from ..summary_generator import SummaryGenerator
except ImportError:
    # Fallback to absolute imports for Docker environment
    from src.gemini_transcription_service.transcribe import TranscriptionService
    from src.gemini_transcription_service.summary_generator import SummaryGenerator
import logging
from dotenv import load_dotenv

load_dotenv()

# Config setup
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.urandom(24)

# Feature flags from env vars
app.config['AUDIO_STORAGE_ENABLED'] = os.getenv('AUDIO_STORAGE_ENABLED', 'false').lower() in ['true', '1', 'yes']
app.config['KEEP_LOCAL_AUDIO'] = os.getenv('KEEP_LOCAL_AUDIO', 'false').lower() in ['true', '1', 'yes']
app.config['GENERATE_SUMMARY'] = os.getenv('GENERATE_SUMMARY', 'false').lower() in ['true', '1', 'yes']

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
app.logger.setLevel(logging.INFO)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    # Check if file extension is supported
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_file(path):
    # Delete temp files
    if os.path.exists(path):
        try:
            os.remove(path)
            app.logger.info(f"Removed: {path}")
        except OSError as e:
            app.logger.error(f"Failed to remove {path}: {e}")

@app.route('/')
def index():
    # Main page
    formatted_extensions = ['.' + ext for ext in ALLOWED_EXTENSIONS]
    return render_template('index.html', allowed_extensions_for_accept=formatted_extensions)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Handle file upload and transcription
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        # Save with unique name
        filename = secure_filename(file.filename)
        uid = str(uuid.uuid4())
        name, ext = os.path.splitext(filename)
        unique_name = f"{name}_{uid}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)
        flash(f'File "{filename}" uploaded successfully. Processing...')

        try:
            app.logger.info(f"Processing: {filepath}")
            
            # Run transcription
            service = TranscriptionService()
            transcript, output_path, _ = service.run(
                filepath,
                output_dir_override=app.config['UPLOAD_FOLDER'],
                store_audio=app.config['AUDIO_STORAGE_ENABLED'],
                generate_summary=False
            )
            
            if transcript is None or output_path is None:
                app.logger.error(f"Transcription failed for {filepath}")
                flash('Transcription failed')
                cleanup_file(filepath)
                return redirect(url_for('index'))

            app.logger.info(f"Transcription complete: {output_path}")
            
            # Clean up if needed
            if not app.config['KEEP_LOCAL_AUDIO']:
                cleanup_file(filepath)
            
            download_name = os.path.basename(output_path)
            return render_template('index.html', transcript=transcript, download_filename=download_name, 
                                  original_filepath=filepath)

        except Exception as e:
            app.logger.error(f"Error: {e}")
            flash(f'An error occurred: {e}')
            cleanup_file(filepath)
            return redirect(url_for('index'))
    else:
        flash('File type not allowed')
        return redirect(request.url)

@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    # Generate summary from transcript
    try:
        data = request.get_json()
        transcript = data.get('transcript', '')
        speaker_mapping = data.get('speaker_mapping', {})
        
        if not transcript:
            return jsonify({'success': False, 'error': 'No transcript provided'}), 400
        
        app.logger.info("Generating meeting summary...")
        summary_generator = SummaryGenerator()
        summary = summary_generator.generate_summary(transcript, speaker_mapping)
        
        if not summary:
            return jsonify({'success': False, 'error': 'Failed to generate summary'}), 500
            
        # Save summary file
        input_path = data.get('input_path')
        output_dir = app.config['UPLOAD_FOLDER']
        summary_path = summary_generator.save_summary_to_file(
            summary=summary,
            input_path=input_path,
            output_dir=output_dir
        )
        
        if summary_path:
            download_name = os.path.basename(summary_path)
            return jsonify({
                'success': True, 
                'summary': summary,
                'download_filename': download_name
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to save summary file'}), 500
        
    except Exception as e:
        app.logger.error(f"Error generating summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/regenerate-summary', methods=['POST'])
def regenerate_summary():
    # Regenerate summary based on feedback
    try:
        data = request.get_json()
        original_transcript = data.get('original_transcript', '')
        previous_summary = data.get('previous_summary', '')
        feedback = data.get('feedback', '')
        
        if not original_transcript or not previous_summary or not feedback:
            return jsonify({'success': False, 'error': 'Missing required information'}), 400
        
        app.logger.info("Regenerating meeting summary based on feedback...")
        summary_generator = SummaryGenerator()
        new_summary = summary_generator.regenerate_summary(
            original_transcript=original_transcript,
            previous_summary=previous_summary,
            feedback=feedback
        )
        
        if not new_summary:
            return jsonify({'success': False, 'error': 'Failed to regenerate summary'}), 500
            
        # Save updated summary
        input_path = data.get('input_path')
        output_dir = app.config['UPLOAD_FOLDER']
        summary_path = summary_generator.save_summary_to_file(
            summary=new_summary,
            input_path=input_path,
            output_dir=output_dir
        )
        
        if summary_path:
            download_name = os.path.basename(summary_path)
            return jsonify({
                'success': True, 
                'summary': new_summary,
                'download_filename': download_name
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to save regenerated summary file'}), 500
        
    except Exception as e:
        app.logger.error(f"Error regenerating summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    # Secure file download
    safe_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
    safe_path = os.path.join(safe_dir, filename)
    if not os.path.abspath(safe_path).startswith(safe_dir):
        flash("Invalid path")
        return redirect(url_for('index'))

    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        flash("File not found")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)