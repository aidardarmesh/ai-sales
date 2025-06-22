# AI Sales Frontend Setup

This Next.js application provides a web interface for real-time audio streaming with the AI Sales backend server.

## Prerequisites

1. **Backend Server**: Make sure your Python WebSocket server (`server.py`) is running on `localhost:8000`
2. **Node.js**: Version 18 or higher
3. **Modern Browser**: Chrome, Firefox, Safari, or Edge with WebRTC support

## Installation

1. **Install dependencies:**
   ```bash
   cd ai-sales-frontend
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   Navigate to `http://localhost:3000`

## Usage

1. **Start Backend Server First:**
   ```bash
   # In the parent directory
   python server.py
   ```

2. **Open Frontend:**
   - Go to `http://localhost:3000`
   - Click "Connect to Server"
   - Allow microphone access when prompted
   - Click "Start Recording" to begin conversation
   - Speak into your microphone
   - Listen for AI responses through your speakers
   - Click "Stop Recording" when done

## Features

- **Real-time WebSocket Connection**: Connects to your Python backend server
- **Audio Recording**: Captures microphone input and streams to server
- **Audio Playback**: Plays AI responses received from Gemini Live API
- **Visual Feedback**: Shows connection status and audio levels
- **Responsive Design**: Works on desktop and mobile devices

## Browser Permissions

The app requires:
- **Microphone Access**: To record your voice
- **Audio Playback**: To play AI responses

## Troubleshooting

### Connection Issues
- Ensure backend server is running on `localhost:8000`
- Check browser console for WebSocket errors
- Verify CORS settings if accessing from different domain

### Audio Issues
- Grant microphone permissions in browser
- Check audio input/output device settings
- Ensure speakers/headphones are connected

### Performance Issues
- Use Chrome for best WebRTC performance
- Close other audio applications
- Check network connection stability

## Development

### File Structure
```
src/
├── app/
│   └── page.tsx          # Main page component
├── components/
│   └── AudioStreamer.tsx # Main audio streaming component
└── ...
```

### Key Components

- **AudioStreamer**: Main component handling WebSocket connection and audio streaming
- **WebSocket Management**: Handles connection lifecycle and message routing
- **Audio Processing**: Records microphone input and plays AI responses
- **UI Controls**: Buttons and status indicators for user interaction

## Production Deployment

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Start production server:**
   ```bash
   npm start
   ```

3. **Update server URLs:**
   - Change `serverUrl` in `AudioStreamer` component
   - Update CORS settings in backend server
   - Configure proper SSL certificates for HTTPS

## Browser Compatibility

- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 11+
- ✅ Edge 79+
- ❌ Internet Explorer (not supported)

## Security Notes

- Microphone access requires HTTPS in production
- WebSocket connections should use WSS in production
- Implement proper authentication for production use
