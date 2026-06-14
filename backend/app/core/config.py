import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cognitive Voice Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "info"
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_password_here@localhost:5432/cognitive_voice_db"
    
    # ASR Whisper Configuration
    WHISPER_MODEL: str = "medium"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_CPU_THREADS: int = 4
    
    # Storage
    AUDIO_UPLOAD_DIR: str = ""
    UPLOAD_DIR: str = ""
    SUPPORTED_AUDIO_EXTENSIONS: list = ["wav", "mp3", "webm", "m4a"]
    MAX_AUDIO_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    
    # Security
    SECRET_KEY: str = "change_me_in_production_secret_key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Ensure upload directory exists
    def create_upload_dir(self) -> None:
        if self.AUDIO_UPLOAD_DIR:
            self.UPLOAD_DIR = self.AUDIO_UPLOAD_DIR
        if not self.UPLOAD_DIR:
            # backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.UPLOAD_DIR = os.path.join(base_dir, "storage", "audio", "sessions")
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
settings.create_upload_dir()
