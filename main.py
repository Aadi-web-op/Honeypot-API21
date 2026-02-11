import os
import logging
import asyncio
import random
import re
import json
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our custom modules
from key_manager import KeyManager
from persona_manager import PersonaManager
from media_handler import MediaHandler
from utils.fake_proof import FakeProofGenerator
from presidio_analyzer import AnalyzerEngine, RecognizerResult

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Azure Compatibility: Ensure static directory exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import joblib for ML loading
import joblib

# -- Global Managers --
key_manager = KeyManager()
persona_manager = PersonaManager()
media_handler = MediaHandler()
fake_proof_generator = FakeProofGenerator()

# Initialize Presidio
try:
    presidio_analyzer = AnalyzerEngine()
except Exception as e:
    logger.warning(f"Presidio Engine failed to load (Model missing?): {e}")
    presidio_analyzer = None

# -- Load ML Models --
scam_classifier = None
tfidf_vectorizer = None
try:
    if os.path.exists("scam_classifier.pkl") and os.path.exists("tfidf_vectorizer.pkl"):
        scam_classifier = joblib.load("scam_classifier.pkl")
        tfidf_vectorizer = joblib.load("tfidf_vectorizer.pkl")
        logger.info("✅ ML Models Loaded Successfully")
    else:
        logger.warning("⚠️ ML Models not found in root directory.")
except Exception as e:
    logger.error(f"⚠️ ML Load Failed: {e}")

# -- In-Memory Storage (Stateless for Hackathon) --
# Format: session_id -> { "history": [], "metadata": {}, "persona": "grandma" }
sessions: Dict[str, Dict] = {}

# -- Data Models --
class ChatRequest(BaseModel):
    session_id: str
    message: str
    sender: str = "scammer"  # scammer or user

# -- Helper Functions --

def redact_pii(text: str) -> str:
    """Redacts phone numbers and emails using Presidio."""
    if not presidio_analyzer:
        return text
        
    try:
        results = presidio_analyzer.analyze(text=text, entities=["PHONE_NUMBER", "EMAIL_ADDRESS"], language='en')
        if not results:
            return text
            
        redacted_text = text
        # Sort results in reverse order to avoid index shifting
        for result in sorted(results, key=lambda x: x.start, reverse=True):
            redacted_text = redacted_text[:result.start] + "<REDACTED>" + redacted_text[result.end:]
        return redacted_text
    except Exception as e:
        logger.error(f"Redaction failed: {e}")
        return text

def extract_upi(text: str) -> Optional[str]:
    """Tries to find a UPI ID in the text."""
    # Pattern: something@something
    upi_pattern = r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}'
    match = re.search(upi_pattern, text)
    if match:
        return match.group(0)
    return None

# -- Endpoints --

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Main Chat Interface.
    1. Redacts PII.
    2. Updates Session History.
    3. Selects Persona (if new session).
    4. Delays response (mimic human).
    5. Calls LLM (with key rotation).
    6. Checks for Trap triggers.
    """
    session_id = request.session_id
    user_msg = request.message
    
    # Initialize session if new
    if session_id not in sessions:
        persona = persona_manager.select_persona(user_msg)
        sessions[session_id] = {
            "history": [], 
            "persona": persona,
            "ip_log": [],
            "traps_triggered": [],
            "extracted_upi": None,
            "last_classification": None
        }
        # Add system prompt to history (hidden from user, but sent to LLM)
        sessions[session_id]["history"].append({"role": "system", "content": persona["system_prompt"]})

    session = sessions[session_id]
    
    # Redact PII for safety before processing/logging
    safe_msg = redact_pii(user_msg)
    
    # Extract UPI if present (update session memory)
    found_upi = extract_upi(safe_msg)
    if found_upi:
        session["extracted_upi"] = found_upi
    
    # Update History
    session["history"].append({"role": "user", "content": safe_msg})
    
    # 3. ML Classification
    scam_type = "unknown"
    confidence = 0.0
    if scam_classifier and tfidf_vectorizer:
        try:
            vec = tfidf_vectorizer.transform([safe_msg])
            scam_type = scam_classifier.predict(vec)[0]
            # Handle predict_proba if available
            if hasattr(scam_classifier, "predict_proba"):
                confidence = float(max(scam_classifier.predict_proba(vec)[0]))
            
            # Store in session for the report
            session["last_classification"] = {"type": scam_type, "conf": confidence}
            logger.info(f"ML Prediction: {scam_type} ({confidence:.2f})")
        except Exception as e:
            logger.error(f"ML Prediction Error: {e}")
    
    # 1. TRAP LOGIC: Check for "Payment" keywords to trigger Fake Proof
    lower_msg = safe_msg.lower()
    img_url = None
    
    # Trigger if they ask for proof AND we have a UPI to send to (or generic)
    if any(x in lower_msg for x in ["screenshot", "proof", "photo", "payment done"]):
        # Use extracted UPI, or fallback to 'scammer@upi'
        target_upi = session["extracted_upi"] or "scammer@bank"
        
        # Generate Proof
        filename = fake_proof_generator.generate_payment_proof("5000", target_upi)
        
        # Create Trap Link (Relative for now)
        img_url = f"/proof/{filename}"
        session["traps_triggered"].append({"type": "fake_proof", "file": filename, "timestamp": "now"})
        
        # Inject constraint to LLM to mention the image
        # We append this as a temporary system instruction for THIS turn only ideally, 
        # but appending to history works for context window.
        session["history"].append({
            "role": "system", 
            "content": f"[SYSTEM INSTRUCTION]: You have just successfully generated a fake GPay payment screenshot. The file link is '{img_url}'. You MUST send this link to the user now. Say 'Here is the screenshot' or similar."
        })

    # 2. Human Delay (The "Grandma Delay")
    delay = random.uniform(4, 8)
    logger.info(f"Delaying response by {delay:.2f} seconds...")
    await asyncio.sleep(delay)
    
    # 3. Get LLM Response
    response_text = await key_manager.chat_completion(session["history"])
    
    # If we generated a link but the LLM didn't mention it (unlikely with instruction), append it.
    if img_url and img_url not in response_text:
        response_text += f"\n\n[Attachment]: {img_url}"
        
    # Update History with AI response
    session["history"].append({"role": "assistant", "content": response_text})
    
    return {"response": response_text}

@app.post("/upload_media")
async def upload_media(session_id: str, file: UploadFile = File(...)):
    """
    Handles Audio/Image uploads.
    """
    content = await file.read()
    
    description = ""
    # Simple mime type check
    if file.content_type and "audio" in file.content_type:
        description = await media_handler.process_audio(content)
    elif file.content_type and "image" in file.content_type:
        description = media_handler.process_image(content)
    else:
        description = "[Unsupported File Type]"
        
    # Inject into chat history as a system observation
    if session_id in sessions:
        sessions[session_id]["history"].append({
            "role": "system", 
            "content": f"[System Observation]: User sent a file. Analysis: {description}"
        })
        
    return {"description": description}

@app.get("/proof/{filename}")
async def get_proof(filename: str, request: Request):
    """
    The Trap Endpoint.
    Logs IP and User Agent when the scammer loads the image.
    """
    # Log the access
    visitor_ip = request.client.host
    user_agent = request.headers.get("user-agent")
    
    logger.warning(f"TRAP TRIGGERED! IP: {visitor_ip}, UA: {user_agent}, File: {filename}")
    
    # Determine which session this belongs to (naive search)
    for sid, data in sessions.items():
        for trap in data["traps_triggered"]:
            if trap.get("file") == filename:
                data["ip_log"].append({"ip": visitor_ip, "ua": user_agent, "timestamp": "now"})
                break

    # Serve the file
    file_path = os.path.join("static", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/report/{session_id}")
async def get_report(session_id: str):
    """Returns the Golden JSON for Judges."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    data = sessions[session_id]
    
    return {
        "session_id": session_id,
        "persona_used": data["persona"]["name"],
        "scammer_ip_logs": data["ip_log"],
        "traps_deployed": data["traps_triggered"],
        "chat_transcript": data["history"]
    }

@app.get("/")
def health_check():
    return {"status": "Scam Honeypot Active", "mode": "Offensive"}
