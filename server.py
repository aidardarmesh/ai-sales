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
    "system_instruction": "You are a helpful assistant and answer in a friendly tone.",
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")
    
    async def send_audio(self, client_id: str, data: bytes):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_bytes(data)

manager = ConnectionManager()

async def handle_client_audio(websocket: WebSocket, session, client_id: str):
    """Receive audio from frontend and send to Gemini"""
    try:
        while True:
            # Receive audio data from frontend
            data = await websocket.receive_bytes()
            logger.info(f"Received {len(data)} bytes from client {client_id}")
            
            # Send to Gemini Live API
            await session.send_realtime_input(
                audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
            )
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected during audio handling")
        raise
    except Exception as e:
        logger.error(f"Error handling client audio for {client_id}: {e}")
        raise

async def handle_gemini_response(websocket: WebSocket, session, client_id: str):
    """Receive audio from Gemini and send to frontend"""
    try:
        async for response in session.receive():
            if response.data is not None:
                logger.info(f"Sending {len(response.data)} bytes to client {client_id}")
                # Send audio data back to frontend
                await manager.send_audio(client_id, response.data)
                
            # Optional: Log additional response information
            if hasattr(response, 'server_content') and response.server_content.model_turn is not None:
                logger.debug(f"Model turn received for client {client_id}")
                
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
        async with client.aio.live.connect(model=model, config=config) as session:
            logger.info(f"Gemini session established for client {client_id}")
            
            # Create tasks for bidirectional communication
            receive_task = asyncio.create_task(
                handle_client_audio(websocket, session, client_id)
            )
            send_task = asyncio.create_task(
                handle_gemini_response(websocket, session, client_id)
            )
            
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
    finally:
        manager.disconnect(client_id)

@app.get("/")
async def root():
    return {
        "message": "AI Sales Audio Server is running",
        "websocket_endpoint": "/ws/audio/{client_id}",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "gemini_model": model
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
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
