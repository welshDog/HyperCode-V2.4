"""
HyperStudio Configuration
Settings management with Pydantic for type safety
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "HyperStudio"
    app_version: str = "1.0.0-mvp"
    environment: str = "development"
    debug: bool = True
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Azure Speech Services
    azure_speech_key: str
    azure_speech_region: str = "uksouth"
    
    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_key: Optional[str] = None
    supabase_storage_bucket: str = "videos"
    
    # GPU/Processing
    gpu_device: int = 0
    max_workers: int = 2
    processing_timeout: int = 300  # 5 minutes max per video
    
    # Paths
    models_dir: str = "models"
    avatars_dir: str = "avatars"
    temp_dir: str = "/tmp/hyperstudio"
    
    # Wav2Lip Settings
    wav2lip_model: str = "wav2lip_gan.pth"
    face_detection_model: str = "s3fd.pth"
    wav2lip_quality: str = "Enhanced"  # Fast, Improved, Enhanced
    
    # Video Settings
    video_fps: int = 25
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "2000k"
    video_resolution: tuple[int, int] = (512, 512)
    
    # Default Voice
    default_voice_id: str = "en-GB-RyanNeural"
    default_avatar_id: str = "broski_default"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Create required directories
def setup_directories():
    """Create necessary directories if they don't exist"""
    os.makedirs(settings.temp_dir, exist_ok=True)
    os.makedirs(settings.models_dir, exist_ok=True)
    os.makedirs(settings.avatars_dir, exist_ok=True)
    os.makedirs(f"{settings.models_dir}/face_detection", exist_ok=True)


# Validate configuration
def validate_config():
    """Validate critical configuration values"""
    errors = []
    
    # Check Azure credentials
    if not settings.azure_speech_key or settings.azure_speech_key == "your_azure_key_here":
        errors.append("AZURE_SPEECH_KEY not configured in .env")
    
    # Check Supabase credentials
    if not settings.supabase_url or "your-project" in settings.supabase_url:
        errors.append("SUPABASE_URL not configured in .env")
    
    if not settings.supabase_key or "your_supabase" in settings.supabase_key:
        errors.append("SUPABASE_KEY not configured in .env")
    
    # Check model files exist
    wav2lip_path = f"{settings.models_dir}/{settings.wav2lip_model}"
    if not os.path.exists(wav2lip_path):
        errors.append(f"Wav2Lip model not found at {wav2lip_path}")
    
    face_det_path = f"{settings.models_dir}/face_detection/{settings.face_detection_model}"
    if not os.path.exists(face_det_path):
        errors.append(f"Face detection model not found at {face_det_path}")
    
    # Check GPU availability
    try:
        import torch
        if not torch.cuda.is_available():
            errors.append("CUDA not available - GPU required for video generation")
    except ImportError:
        errors.append("PyTorch not installed")
    
    return errors


def get_model_paths():
    """Get full paths to model files"""
    return {
        "wav2lip": f"{settings.models_dir}/{settings.wav2lip_model}",
        "face_detection": f"{settings.models_dir}/face_detection/{settings.face_detection_model}",
    }


def get_avatar_path(avatar_id: str) -> str:
    """Get full path to avatar image"""
    return f"{settings.avatars_dir}/{avatar_id}.png"
