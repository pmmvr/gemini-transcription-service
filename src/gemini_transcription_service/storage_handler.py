import os
import time
import logging
from google import genai
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    bucket: str
    enabled: bool
    prefix: str


class StorageHandler:
    def __init__(self, file_type="transcript"):
        self.file_type = file_type.lower()
        self.client = None
        self.config = self._load_config()

    def _load_config(self) -> StorageConfig:
        # Load config based on file type
        if self.file_type == "audio":
            bucket = os.getenv("AUDIO_BUCKET_NAME", os.getenv("TRANSCRIPT_BUCKET_NAME"))
            enabled = os.getenv("AUDIO_STORAGE_ENABLED", "false").lower() in ["true", "1", "yes"]
            prefix = os.getenv("AUDIO_PATH_PREFIX", "audio/")
            if prefix and not prefix.endswith('/'):
                prefix += '/'
        elif self.file_type == "summary":
            bucket = os.getenv("SUMMARY_BUCKET_NAME", os.getenv("TRANSCRIPT_BUCKET_NAME"))
            enabled = os.getenv("SUMMARY_STORAGE_ENABLED", "false").lower() in ["true", "1", "yes"]
            prefix = os.getenv("SUMMARY_PATH_PREFIX", "summaries/")
            if prefix and not prefix.endswith('/'):
                prefix += '/'
        else:
            bucket = os.getenv("TRANSCRIPT_BUCKET_NAME")
            enabled = os.getenv("TRANSCRIPT_STORAGE_ENABLED", "false").lower() in ["true", "1", "yes"]
            prefix = os.getenv("TRANSCRIPT_PATH_PREFIX", "")

        return StorageConfig(bucket=bucket, enabled=enabled, prefix=prefix)
        
    def initialize(self) -> bool:
        # Set up GCS client if storage is enabled
        if not self.config.enabled:
            logger.info(f"{self.file_type} storage disabled")
            return False
            
        if not self.config.bucket:
            logger.warning(f"No bucket for {self.file_type}")
            return False
            
        try:
            logger.info(f"Connecting to {self.config.bucket}")
            self.client = storage.Client()
            
            if not self.client.bucket(self.config.bucket).exists():
                logger.warning(f"Bucket not found: {self.config.bucket}")
                return False
                
            logger.info("GCS connection established")
            return True
        except Exception as e:
            logger.error(f"GCS connection failed: {e}")
            self.client = None
            return False
    
    def upload_file(self, path: str, dest_path: Optional[str] = None, prevent_overwrite: bool = True) -> Optional[str]:
        # Upload file to GCS bucket
        if not self.config.enabled or not self.client:
            return None

        if not os.path.exists(path):
            logger.error(f"File not found: {path}")
            return None

        try:
            bucket = self.client.bucket(self.config.bucket)

            if not dest_path:
                name = os.path.basename(path)

                # Add timestamp to filename to prevent overwriting by default
                if prevent_overwrite:
                    import time
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    name_parts = os.path.splitext(name)
                    name = f"{name_parts[0]}_{timestamp}{name_parts[1]}"

                dest_path = f"{self.config.prefix}{name}"

            blob = bucket.blob(dest_path)
            blob.upload_from_filename(path)

            uri = f"gs://{self.config.bucket}/{dest_path}"
            logger.info(f"Uploaded to {uri}")
            return uri
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None

    def is_enabled(self) -> bool:
        # Check if storage is enabled and client exists
        return self.config.enabled and self.client is not None


class AudioStorageHandler(StorageHandler):
    def __init__(self):
        super().__init__(file_type="audio")


class GCSHandler(StorageHandler):
    def __init__(self):
        super().__init__(file_type="transcript")


class SummaryStorageHandler(StorageHandler):
    def __init__(self):
        super().__init__(file_type="summary")


def upload_file(client: genai.Client, path: str, store_audio: Optional[bool] = None) -> Optional[genai.types.File]:
    # Upload file to Gemini API with optional GCS backup
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    if store_audio is None:
        store_audio = os.getenv("AUDIO_STORAGE_ENABLED", "false").lower() in ["true", "1", "yes"]
    
    backup_uri = None
    if store_audio:
        try:
            handler = StorageHandler(file_type="audio")
            if handler.initialize():
                backup_uri = handler.upload_file(path)
        except Exception as e:
            logger.warning(f"GCS backup failed: {e}")

    file = None 
    try:
        name = os.path.basename(path)
        logger.info(f"Uploading {name} to Gemini")
        file = client.files.upload(file=str(path))

        # Wait for file processing to complete
        while file.state.name == "PROCESSING":
            time.sleep(5)  
            file = client.files.get(name=file.name)

        if file.state.name == "ACTIVE":
            logger.info(f"File ready: {file.name}")
            if backup_uri:
                logger.info(f"Backup at: {backup_uri}")
            return file
        
        try:
            client.files.delete(name=file.name)
        except:
            pass
        
        raise ValueError(f"File processing failed: {file.state.name}")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        if file:
            try:
                client.files.delete(name=file.name)
            except:
                pass
        raise


def delete_uploaded_file(client: genai.Client, file: genai.types.File):
    # Clean up file from Gemini API
    if not file or not file.name:
        return

    try:
        client.files.delete(name=file.name)
        logger.info(f"Deleted {file.name}")
    except Exception as e:
        logger.warning(f"Delete failed: {e}")