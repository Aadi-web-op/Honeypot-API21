import os
import logging
import httpx
import pytesseract
import cv2
import numpy as np
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Pytesseract Path (Adjust if needed/detected)
# On Azure, this likely requires tesseract installed in the container
# For windowns local, it usually needs a path. Assumed in PATH or default.

class MediaHandler:
    def __init__(self):
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")

    async def process_audio(self, audio_bytes: bytes) -> str:
        """Sends audio to OpenRouter Whisper for transcription."""
        if not self.openrouter_key:
            return "[Error: No OpenRouter Key for Audio]"

        try:
            # OpenRouter Audio Transcription (Whisper)
            # Note: Verify OpenRouter specific endpoint for audio or use OpenAI compatible
            # Standard OpenAI format: https://api.openrouter.ai/api/v1/audio/transcriptions
            
            async with httpx.AsyncClient() as client:
                files = {'file': ('audio.mp3', audio_bytes, 'audio/mpeg')}
                response = await client.post(
                    "https://openrouter.ai/api/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.openrouter_key}"},
                    data={"model": "openai/whisper-large-v3-turbo"}, # Using turbo or large
                    files=files,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json().get('text', '')
        except Exception as e:
            logger.error(f"Audio Transcription Failed: {e}")
            return "[Audio Processing Failed]"

    def process_image(self, image_bytes: bytes) -> str:
        """Extracts text via OCR and decodes QR codes."""
        text_content = ""
        qr_content = ""

        try:
            # 1. OCR with Pytesseract
            image = Image.open(io.BytesIO(image_bytes))
            text_content = pytesseract.image_to_string(image)
            
            # 2. QR Code with OpenCV
            nparr = np.frombuffer(image_bytes, np.uint8)
            cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            detector = cv2.QRCodeDetector()
            data, _, _ = detector.detectAndDecode(cv_img)
            if data:
                qr_content = f" [QR Code Data: {data}]"
            
            final_output = f"[Image Content: {text_content.strip()}{qr_content}]"
            return final_output

        except Exception as e:
            logger.error(f"Image Processing Failed: {e}")
            return "[Image Processing Failed]"
