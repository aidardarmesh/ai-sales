# AI Sales Audio Server

A real-time WebSocket server that enables voice conversations with Google's Gemini Live API. This server acts as a bridge between web clients and the Gemini AI model, handling audio streaming and processing.

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Modern web browser with WebRTC support

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd ai-sales
   ```

2. **Install Python dependencies:**
   ```bash
   pip install fastapi uvicorn websockets google-generativeai python-dotenv
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```bash
   echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
   ```

4. **Launch the server:**
   ```bash
   python server.py
   ```

The server will start on `http://localhost:8000`

## 📋 Environment Setup

### Required Environment Variables

Create a `.env` file with the following:

```env
GEMINI_API_KEY=your_actual_gemini_api_key
```

### Getting a Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

## 🔧 Server Configuration

### Default Settings

- **Host:** `0.0.0.0` (accepts connections from any IP)
- **Port:** `8000`
- **Model:** `gemini-2.5-flash-preview-native-audio-dialog`
- **Audio Format:** PCM, 16kHz input, 24kHz output
- **WebSocket Endpoint:** `/ws/audio/{client_id}`

### Customizing Configuration

Edit `server.py` to modify:

```python
# Change the Gemini model
model = "gemini-2.5-flash-preview-native-audio-dialog"

# Modify system instruction
config = {
    "response_modalities": ["AUDIO"],
    "system_instruction": "Your custom AI assistant instructions here.",
}

# Change server port
uvicorn.run("server:app", host="0.0.0.0", port=8080)
```

## 🌐 API Endpoints

### WebSocket Connection
```
ws://localhost:8000/ws/audio/{client_id}
```
- **client_id**: Unique identifier for each client connection
- **Protocol**: Binary WebSocket for audio streaming
- **Audio Format**: PCM audio data

### HTTP Endpoints

#### Health Check
```
GET http://localhost:8000/health
```
Returns server status and active connection count.

#### Server Info
```
GET http://localhost:8000/
```
Returns basic server information and WebSocket endpoint details.

## 🎵 Audio Specifications

### Input Audio (Client → Server → Gemini)
- **Format:** PCM
- **Sample Rate:** 16kHz
- **Channels:** Mono (1 channel)
- **Bit Depth:** 16-bit

### Output Audio (Gemini → Server → Client)
- **Format:** PCM
- **Sample Rate:** 24kHz
- **Channels:** Mono (1 channel)
- **Bit Depth:** 16-bit

## 🔌 Client Integration

### WebSocket Connection Example

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/audio/my_client_id');

// Send audio data (binary)
ws.send(audioBuffer);

// Receive audio data
ws.onmessage = (event) => {
    const audioData = event.data; // Binary audio data
    // Process and play audio
};
```

### Frontend Applications

- **Next.js Frontend:** Available in `ai-sales-frontend/` directory
- **Custom Integration:** Use any WebSocket-capable frontend framework

## 🚦 Running the Server

### Development Mode
```bash
python server.py
```

### Production Mode
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 1
```

### With Custom Configuration
```bash
uvicorn server:app --host 127.0.0.1 --port 8080 --reload
```

## 📊 Monitoring and Logging

### Log Levels
The server provides detailed logging:
- **INFO**: Connection events, audio data flow
- **ERROR**: Connection failures, API errors
- **DEBUG**: Detailed WebSocket message information

### Health Monitoring
Check server health:
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "active_connections": 2,
  "gemini_model": "gemini-2.5-flash-preview-native-audio-dialog"
}
```

## 🛠 Troubleshooting

### Common Issues

#### 1. API Key Not Found
```
Error: GEMINI_API_KEY not found in environment variables
```
**Solution:** Create `.env` file with your Gemini API key

#### 2. Port Already in Use
```
Error: [Errno 48] Address already in use
```
**Solution:** Kill existing process or use different port:
```bash
lsof -ti:8000 | xargs kill -9
# or
uvicorn server:app --port 8001
```

#### 3. WebSocket Connection Failed
**Check:**
- Server is running on correct port
- Firewall settings allow connections
- Client URL matches server address

#### 4. Audio Quality Issues
**Verify:**
- Audio format matches specifications
- Sample rates are correct (16kHz input, 24kHz output)
- Network connection is stable

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔒 Security Considerations

### Development
- Server accepts connections from any IP (`0.0.0.0`)
- CORS allows all origins (`allow_origins=["*"]`)

### Production Recommendations
1. **Restrict CORS origins:**
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

2. **Use HTTPS/WSS:**
   ```python
   uvicorn.run("server:app", host="0.0.0.0", port=443, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
   ```

3. **Implement authentication:**
   Add API key validation or JWT tokens

4. **Rate limiting:**
   Implement connection and request rate limits

## 📁 Project Structure

```
ai-sales/
├── server.py              # Main WebSocket server
├── main.py               # Original one-shot script
├── .env                  # Environment variables
├── README.md             # This file
└── ai-sales-frontend/    # Next.js frontend application
    ├── src/
    ├── package.json
    └── SETUP.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both server and frontend
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review server logs for error details
3. Verify API key and network connectivity
4. Test with the provided frontend application

---

**Happy coding! 🎉**
