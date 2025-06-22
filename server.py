from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import numpy as np

# Add after other imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Sales Audio Server", version="1.0.0")

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model = "gemini-2.5-flash-preview-native-audio-dialog"

# Configuration for Gemini
config = {
    "response_modalities": ["AUDIO"],
    "system_instruction": "You are a helpful AI sales assistant. Answer questions about products and services in a friendly, professional tone. Keep responses concise and engaging.",
}

class AudioBuffer:
    def __init__(self, sample_rate=16000, silence_threshold=0.01, silence_duration=1.0):
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.buffer = []
        self.silence_samples = 0
        self.min_audio_length = sample_rate * 0.5  # Minimum 0.5 seconds
        self.max_audio_length = sample_rate * 10   # Maximum 10 seconds
        
    def add_chunk(self, pcm_data: bytes) -> bytes:
        """Add PCM chunk and return complete utterance when speech ends"""
        # Convert bytes to numpy array (int16)
        audio_samples = np.frombuffer(pcm_data, dtype=np.int16)
        
        # Calculate RMS (Root Mean Square) for volume detection
        rms = np.sqrt(np.mean(audio_samples.astype(np.float32) ** 2)) / 32768.0
        
        # Add to buffer
        self.buffer.extend(audio_samples)
        
        # Check if we're in silence
        if rms < self.silence_threshold:
            self.silence_samples += len(audio_samples)
        else:
            self.silence_samples = 0  # Reset silence counter on speech
        
        # Calculate silence duration
        silence_duration = self.silence_samples / self.sample_rate
        
        # Check if we should send the buffer
        should_send = False
        
        if len(self.buffer) >= self.max_audio_length:
            # Send if buffer is too long
            should_send = True
            logger.info(f"Sending audio: max length reached ({len(self.buffer)} samples)")
        elif (len(self.buffer) >= self.min_audio_length and 
              silence_duration >= self.silence_duration):
            # Send if we have enough audio and detected silence
            should_send = True
            logger.info(f"Sending audio: speech ended ({len(self.buffer)} samples, {silence_duration:.1f}s silence)")
        
        if should_send:
            # Convert back to bytes and clear buffer
            complete_audio = np.array(self.buffer, dtype=np.int16).tobytes()
            self.buffer = []
            self.silence_samples = 0
            return complete_audio
        
        return b''  # No complete utterance yet

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
        self.gemini_sessions: dict = {}
        self.audio_buffers: dict = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.audio_buffers[client_id] = AudioBuffer()
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.gemini_sessions:
            del self.gemini_sessions[client_id]
        if client_id in self.audio_buffers:
            del self.audio_buffers[client_id]
        logger.info(f"Client {client_id} disconnected")
    
    async def send_audio(self, client_id: str, data: bytes):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_bytes(data)
    
    def get_audio_buffer(self, client_id: str) -> AudioBuffer:
        return self.audio_buffers.get(client_id)
    
    def set_gemini_session(self, client_id: str, session):
        self.gemini_sessions[client_id] = session
    
    def get_gemini_session(self, client_id: str):
        return self.gemini_sessions.get(client_id)

manager = ConnectionManager()

async def handle_client_audio(websocket: WebSocket, session, client_id: str):
    """Receive PCM audio chunks, buffer them, and send complete utterances to Gemini"""
    audio_buffer = manager.get_audio_buffer(client_id)
    
    try:
        while True:
            # Receive PCM audio chunk from frontend
            data = await websocket.receive_bytes()
            logger.debug(f"Received {len(data)} bytes PCM chunk from client {client_id}")
            
            # Add chunk to buffer and check if we have a complete utterance
            complete_audio = audio_buffer.add_chunk(data)
            
            if complete_audio:
                logger.info(f"Sending complete utterance to Gemini: {len(complete_audio)} bytes for client {client_id}")
                
                # Send complete utterance to Gemini Live API
                await session.send_realtime_input(
                    audio=types.Blob(data=complete_audio, mime_type="audio/pcm;rate=16000")
                )
                logger.info(f"Successfully sent complete utterance to Gemini for client {client_id}")
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected during audio handling")
        raise
    except Exception as e:
        logger.error(f"Error handling client audio for {client_id}: {e}")
        raise

async def handle_gemini_response(websocket: WebSocket, session, client_id: str):
    """Receive audio from Gemini and send to frontend"""
    try:
        logger.info(f"Starting to listen for Gemini responses for client {client_id}")
        
        async for response in session.receive():
            if response.data is not None:
                logger.info(f"Received {len(response.data)} bytes from Gemini for client {client_id}")
                # Send audio data back to frontend
                await manager.send_audio(client_id, response.data)
                logger.info(f"Sent audio response to client {client_id}")
                
            # Log additional response information
            if hasattr(response, 'server_content') and response.server_content and response.server_content.model_turn is not None:
                logger.info(f"Model turn received for client {client_id}")
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected during response handling")
        raise
    except Exception as e:
        logger.error(f"Error handling Gemini response for {client_id}: {e}")
        raise

@app.websocket("/ws/audio/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    
    try:
        logger.info(f"Establishing Gemini session for client {client_id}")
        async with client.aio.live.connect(model=model, config=config) as session:
            logger.info(f"Gemini session established for client {client_id}")
            manager.set_gemini_session(client_id, session)
            
            # Create tasks for bidirectional communication
            receive_task = asyncio.create_task(
                handle_client_audio(websocket, session, client_id)
            )
            send_task = asyncio.create_task(
                handle_gemini_response(websocket, session, client_id)
            )
            
            logger.info(f"Started audio streaming tasks for client {client_id}")
            
            # Wait for either task to complete or fail
            done, pending = await asyncio.wait(
                [receive_task, send_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for client {client_id}")
    except Exception as e:
        logger.error(f"Error in websocket connection for client {client_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        manager.disconnect(client_id)

@app.get("/")
async def root():
    return {
        "message": "AI Sales Audio Server is running",
        "websocket_endpoint": "/ws/audio/{client_id}",
        "status": "healthy",
        "model": model
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "gemini_model": model,
        "timestamp": time.time()
    }

# Optional: Serve static files if you want to host a simple frontend
# app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    
    # Check if API key is available
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY not found in environment variables")
        exit(1)
    
    logger.info("Starting AI Sales Audio Server...")
    logger.info("Server now receives PCM audio directly from frontend - no conversion needed!")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
