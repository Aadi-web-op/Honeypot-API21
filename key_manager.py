import os
import logging
from typing import Optional, Dict, Any, List
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self):
        self.groq_keys = [
            os.getenv("GROQ_API_KEY_1"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3")
        ]
        # Filter out None values
        self.groq_keys = [k for k in self.groq_keys if k]
        self.current_groq_index = 0
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        # Models
        self.GROQ_MODEL = "llama3-70b-8192"
        self.OPENROUTER_MODEL = "meta-llama/llama-3.1-70b-instruct"

    def _get_current_groq_key(self) -> Optional[str]:
        if not self.groq_keys:
            return None
        return self.groq_keys[self.current_groq_index]

    def _rotate_groq_key(self):
        """Switches to the next Groq key."""
        if not self.groq_keys:
            return
        self.current_groq_index = (self.current_groq_index + 1) % len(self.groq_keys)
        logger.info(f"Rotated to Groq Key Index: {self.current_groq_index}")

    async def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Tries to get a completion from Groq (rotating keys on failure).
        If all Groq keys fail, falls back to OpenRouter.
        """
        
        # 1. Try Groq (with rotation)
        for _ in range(len(self.groq_keys)):
            current_key = self._get_current_groq_key()
            if not current_key:
                break
                
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {current_key}"},
                        json={
                            "model": self.GROQ_MODEL,
                            "messages": messages,
                            "temperature": 0.7
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 429: # Rate Limit
                        logger.warning(f"Groq Rate Limit on Key {self.current_groq_index}. Rotating...")
                        self._rotate_groq_key()
                        continue # Try next key
                        
                    response.raise_for_status()
                    return response.json()['choices'][0]['message']['content']
                    
            except Exception as e:
                logger.error(f"Groq Error (Key {self.current_groq_index}): {e}")
                self._rotate_groq_key()
                # Continue loop to try next key

        # 2. OpenRouter Failover
        logger.warning("All Groq keys failed or exhausted. Switching to OpenRouter.")
        if not self.openrouter_key:
            return "Server Error: No valid API keys available."

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                         "HTTP-Referer": "https://hacktrinity.vercel.app/",
                         "X-Title": "HackTrinity HoneyPot"
                    },
                    json={
                        "model": self.OPENROUTER_MODEL,
                        "messages": messages
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenRouter Failed: {e}")
            return "I am having trouble connecting. Can you say that again?"
