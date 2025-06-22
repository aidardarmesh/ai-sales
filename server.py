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
import time

# Configure logging
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

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
        self.gemini_sessions: dict = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.gemini_sessions:
            del self.gemini_sessions[client_id]
        logger.info(f"Client {client_id} disconnected")
    
    async def send_audio(self, client_id: str, data: bytes):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_bytes(data)
    
    def set_gemini_session(self, client_id: str, session):
        self.gemini_sessions[client_id] = session
    
    def get_gemini_session(self, client_id: str):
        return self.gemini_sessions.get(client_id)

manager = ConnectionManager()

async def handle_client_audio(websocket: WebSocket, session, client_id: str):
    """Receive PCM audio from frontend and send directly to Gemini"""
    try:
        while True:
            # Receive PCM audio data from frontend
            data = await websocket.receive_bytes()
            logger.info(f"Received {len(data)} bytes PCM from client {client_id}")
            
            # Send PCM data directly to Gemini Live API (no conversion needed!)
            await session.send_realtime_input(
                audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
            )
            logger.info(f"Successfully sent {len(data)} bytes PCM to Gemini for client {client_id}")
            
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
