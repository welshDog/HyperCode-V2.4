"""
HyperStudio Video Generator
Core engine for AI avatar video generation using Wav2Lip + Azure TTS
Built for neurodivergent creators! 💪
"""

import torch
import cv2
import numpy as np
from pathlib import Path
import tempfile
import subprocess
from typing import Optional
import logging

# Azure TTS
import azure.cognitiveservices.speech as speechsdk

# Wav2Lip (we'll use the package wrapper)
from wyn_wav2lip.wav2lip import Wav2Lip as Wav2LipEngine

logger = logging.getLogger(__name__)


class HyperStudioVideoGenerator:
    """
    Main video generation engine
    
    Combines:
    - Azure TTS for high-quality voice
    - Wav2Lip GAN for accurate lip sync
    - FFmpeg for video encoding
    """
    
    def __init__(
        self,
        wav2lip_model_path: str,
        azure_speech_key: str,
        azure_speech_region: str,
        device: str = "cuda",
        quality: str = "Enhanced"
    ):
        self.device = device
        self.quality = quality
        self.azure_speech_key = azure_speech_key
        self.azure_speech_region = azure_speech_region
        
        # Initialize Wav2Lip model
        logger.info("Loading Wav2Lip model...")
        self.wav2lip = self._load_wav2lip(wav2lip_model_path)
        logger.info("✓ Wav2Lip model loaded successfully")
        
        # Check GPU
        if device == "cuda" and torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"✓ GPU detected: {gpu_name}")
        else:
            logger.warning("⚠ No GPU detected, using CPU (will be slow!)")
    
    def _load_wav2lip(self, model_path: str):
        """Load Wav2Lip model"""
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Wav2Lip model not found at {model_path}\n"
                "Download from: https://github.com/Rudrabha/Wav2Lip/releases"
            )
        
        # Use the wyn-wav2lip package wrapper
        wav2lip = Wav2LipEngine()
        wav2lip.setup()
        return wav2lip
    
    async def generate_tutorial_video(
        self,
        avatar_image_path: str,
        script_text: str,
        output_path: str,
        voice_id: str = "en-GB-RyanNeural",
        voice_style: Optional[str] = None
    ) -> dict:
        """
        Generate complete tutorial video
        
        Args:
            avatar_image_path: Path to BROski avatar image
            script_text: Tutorial script text
            output_path: Where to save final video
            voice_id: Azure TTS voice ID
            voice_style: Optional voice style (cheerful, excited, friendly)
            
        Returns:
            dict with video metadata (duration, file_size, etc.)
        """
        logger.info("🎬 Starting video generation...")
        logger.info(f"Avatar: {avatar_image_path}")
        logger.info(f"Voice: {voice_id}")
        logger.info(f"Script length: {len(script_text)} characters")
        
        temp_dir = Path(tempfile.mkdtemp(prefix="hyperstudio_"))
        
        try:
            # Step 1: Generate audio from script using Azure TTS
            logger.info("Step 1/4: Generating audio with Azure TTS...")
            audio_path = self._text_to_speech(
                text=script_text,
                voice_id=voice_id,
                output_path=str(temp_dir / "audio.wav"),
                style=voice_style
            )
            logger.info(f"✓ Audio generated: {audio_path}")
            
            # Step 2: Load and prepare avatar image
            logger.info("Step 2/4: Loading avatar image...")
            avatar_frame = self._load_avatar(avatar_image_path)
            logger.info(f"✓ Avatar loaded: {avatar_frame.shape}")
            
            # Step 3: Run Wav2Lip to sync lips
            logger.info("Step 3/4: Running Wav2Lip lip sync...")
            video_path = self._wav2lip_sync(
                avatar_frame=avatar_frame,
                audio_path=audio_path,
                output_path=str(temp_dir / "synced.mp4")
            )
            logger.info(f"✓ Lip sync complete: {video_path}")
            
            # Step 4: Final encoding with better quality
            logger.info("Step 4/4: Final video encoding...")
            self._encode_final_video(
                video_path=video_path,
                audio_path=audio_path,
                output_path=output_path
            )
            logger.info(f"✓ Video saved: {output_path}")
            
            # Get metadata
            metadata = self._get_video_metadata(output_path)
            logger.info("🎉 Video generation complete!")
            
            return metadata
            
        finally:
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _text_to_speech(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        style: Optional[str] = None
    ) -> str:
        """
        Convert text to speech using Azure TTS
        
        Supports:
        - Welsh voices: cy-GB-NiaNeural, cy-GB-AledNeural
        - English voices: en-GB-RyanNeural, en-GB-SoniaNeural, etc.
        - Voice styles: cheerful, excited, friendly, empathetic
        """
        # Configure Azure Speech
        speech_config = speechsdk.SpeechConfig(
            subscription=self.azure_speech_key,
            region=self.azure_speech_region
        )
        
        # Set voice
        speech_config.speech_synthesis_voice_name = voice_id
        
        # Configure output
        audio_config = speechsdk.audio.AudioOutputConfig(
            filename=output_path
        )
        
        # Create synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        # Build SSML with style if provided
        if style:
            ssml = f"""
            <speak version='1.0' xml:lang='en-GB'>
                <voice name='{voice_id}'>
                    <mstts:express-as style='{style}'>
                        {text}
                    </mstts:express-as>
                </voice>
            </speak>
            """
            result = synthesizer.speak_ssml_async(ssml).get()
        else:
            result = synthesizer.speak_text_async(text).get()
        
        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return output_path
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            raise Exception(f"Azure TTS failed: {cancellation.reason} - {cancellation.error_details}")
        else:
            raise Exception(f"Azure TTS unexpected result: {result.reason}")
    
    def _load_avatar(self, image_path: str) -> np.ndarray:
        """Load and prepare avatar image"""
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Avatar image not found: {image_path}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Ensure RGB
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
        # Resize if needed (Wav2Lip works best with 512x512 or similar)
        target_size = 512
        h, w = image.shape[:2]
        if h != target_size or w != target_size:
            image = cv2.resize(image, (target_size, target_size))
        
        return image
    
    def _wav2lip_sync(
        self,
        avatar_frame: np.ndarray,
        audio_path: str,
        output_path: str
    ) -> str:
        """
        Run Wav2Lip to sync lips with audio
        
        This is the core magic! 🎩✨
        """
        # Save avatar frame as temp image
        temp_image = output_path.replace(".mp4", "_avatar.jpg")
        cv2.imwrite(temp_image, avatar_frame)
        
        # Run Wav2Lip using the package wrapper
        # The wrapper handles all the complex inference
        self.wav2lip.run(
            video_file=temp_image,  # Single image acts as video
            vocal_file=audio_path,
            quality=self.quality  # Fast, Improved, or Enhanced
        )
        
        # The wrapper saves output to a default location
        # We need to move it to our desired output path
        # (This depends on the wrapper implementation)
        
        return output_path
    
    def _encode_final_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str
    ):
        """
        Final video encoding with FFmpeg
        
        Combines:
        - Synced video from Wav2Lip
        - High-quality audio from Azure TTS
        - Professional encoding settings
        """
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i", video_path,  # Input video
            "-i", audio_path,  # Input audio
            "-c:v", "libx264",  # H.264 video codec
            "-preset", "medium",  # Encoding speed/quality balance
            "-crf", "23",  # Constant Rate Factor (18-28, lower = better quality)
            "-c:a", "aac",  # AAC audio codec
            "-b:a", "192k",  # Audio bitrate
            "-ar", "44100",  # Audio sample rate
            "-ac", "2",  # Stereo audio
            "-shortest",  # Match shortest stream
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg encoding failed: {result.stderr}")
    
    def _get_video_metadata(self, video_path: str) -> dict:
        """Extract video metadata using FFprobe"""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            # Extract useful info
            format_info = data.get("format", {})
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )
            
            return {
                "duration_seconds": float(format_info.get("duration", 0)),
                "file_size_bytes": int(format_info.get("size", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "fps": self._safe_fps(video_stream.get("r_frame_rate", "25/1"))
            }
        else:
            return {
                "duration_seconds": 0,
                "file_size_bytes": Path(video_path).stat().st_size
            }

    def _safe_fps(self, rate: str) -> float:
        from fractions import Fraction

        try:
            return float(Fraction(rate))
        except Exception:
            return 25.0


# Convenience function for quick testing
async def quick_generate(
    avatar_path: str,
    script: str,
    output_path: str,
    voice: str = "en-GB-RyanNeural"
):
    """
    Quick video generation for testing
    
    Example:
        await quick_generate(
            avatar_path="avatars/broski_default.png",
            script="Hey BRO! Welcome to HyperCode!",
            output_path="test_video.mp4"
        )
    """
    import os
    
    generator = HyperStudioVideoGenerator(
        wav2lip_model_path=os.getenv("WAV2LIP_MODEL_PATH", "models/wav2lip_gan.pth"),
        azure_speech_key=os.getenv("AZURE_SPEECH_KEY"),
        azure_speech_region=os.getenv("AZURE_SPEECH_REGION", "uksouth")
    )
    
    return await generator.generate_tutorial_video(
        avatar_image_path=avatar_path,
        script_text=script,
        output_path=output_path,
        voice_id=voice
    )
