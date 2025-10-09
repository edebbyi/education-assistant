import os
import requests
import tempfile
from typing import Optional

class VoiceSynthesizer:
    def __init__(self, api_key: str = None, voice_id: str = None):
        # Use provided API key or fallback to environment variable
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        # Use default voice or allow user to specify their own
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice
        self.api_url = "https://api.elevenlabs.io/v1/text-to-speech"
        self.timeout = 30  # Increased timeout to 30 seconds for better reliability

    def generate_speech(self, text: str) -> Optional[str]:
        """Convert text to speech using ElevenLabs API"""
        if not self.api_key:
            print("ElevenLabs API key not found")
            return None

        try:
            # Prepare headers and data
            headers = {
                "Accept": "audio/mpeg",
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }

            # Limit text length and clean it for better processing
            cleaned_text = text[:2000].strip()  # Increased limit but still reasonable
            if not cleaned_text:
                return None

            data = {
                "text": cleaned_text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.75,  # Increased for better quality
                    "similarity_boost": 0.75  # Increased for better quality
                }
            }

            # Make API request with retry logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.api_url}/{self.voice_id}",
                        json=data,
                        headers=headers,
                        timeout=self.timeout
                    )

                    if response.status_code == 200:
                        # Save audio to temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                            tmp_file.write(response.content)
                            return tmp_file.name
                    else:
                        print(f"Error from ElevenLabs API: {response.text}")
                        if attempt < max_retries - 1:
                            continue
                        return None

                except requests.Timeout:
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt + 1} timed out, retrying...")
                        continue
                    print("Speech generation timed out after all retries")
                    return None

                except Exception as e:
                    print(f"Error generating speech on attempt {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        continue
                    return None

        except Exception as e:
            print(f"Unexpected error in speech generation: {str(e)}")
            return None

    def set_voice(self, voice_id: str) -> None:
        """Set voice ID for synthesis"""
        self.voice_id = voice_id