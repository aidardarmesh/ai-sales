'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

interface AudioStreamerProps {
  serverUrl?: string;
  clientId?: string;
}

export default function AudioStreamer({ 
  serverUrl = 'ws://localhost:8000', 
  clientId = 'demo_client' 
}: AudioStreamerProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState('Ready');
  const [audioLevel, setAudioLevel] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<Uint8Array[]>([]);
  const isPlayingRef = useRef(false);

  // Initialize WebSocket connection
  const connectWebSocket = useCallback(() => {
    try {
      const ws = new WebSocket(`${serverUrl}/ws/audio/${clientId}`);
      
      ws.onopen = () => {
        setIsConnected(true);
        setStatus('Connected to server');
        console.log('WebSocket connected');
      };

      ws.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          const arrayBuffer = await event.data.arrayBuffer();
          const audioData = new Uint8Array(arrayBuffer);
          audioQueueRef.current.push(audioData);
          
          if (!isPlayingRef.current) {
            playAudioQueue();
          }
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setStatus('Disconnected from server');
        console.log('WebSocket disconnected');
      };

      ws.onerror = (error) => {
        setStatus('Connection error');
        console.error('WebSocket error:', error);
      };

      wsRef.current = ws;
    } catch (error) {
      setStatus('Failed to connect');
      console.error('Connection failed:', error);
    }
  }, [serverUrl, clientId]);

  // Play audio queue
  const playAudioQueue = async () => {
    if (audioQueueRef.current.length === 0 || isPlayingRef.current) return;
    
    isPlayingRef.current = true;
    
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }

      while (audioQueueRef.current.length > 0) {
        const audioData = audioQueueRef.current.shift()!;
        
        // Convert PCM data to AudioBuffer (assuming 24kHz, 16-bit, mono from Gemini)
        const sampleRate = 24000;
        const audioBuffer = audioContextRef.current.createBuffer(1, audioData.length / 2, sampleRate);
        const channelData = audioBuffer.getChannelData(0);
        
        // Convert 16-bit PCM to float32
        for (let i = 0; i < channelData.length; i++) {
          const sample = (audioData[i * 2] | (audioData[i * 2 + 1] << 8));
          channelData[i] = sample < 32768 ? sample / 32768 : (sample - 65536) / 32768;
        }
        
        const source = audioContextRef.current.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContextRef.current.destination);
        
        await new Promise<void>((resolve) => {
          source.onended = () => resolve();
          source.start();
        });
      }
    } catch (error) {
      console.error('Error playing audio:', error);
    } finally {
      isPlayingRef.current = false;
    }
  };

  // Start recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      
      streamRef.current = stream;
      
      // Setup audio analysis for visual feedback
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      source.connect(analyserRef.current);
      
      // Start audio level monitoring
      monitorAudioLevel();

      // Setup MediaRecorder for WebSocket streaming
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          // Convert to PCM format expected by the server
          const arrayBuffer = await event.data.arrayBuffer();
          wsRef.current.send(arrayBuffer);
        }
      };

      mediaRecorder.start(100); // Send data every 100ms
      mediaRecorderRef.current = mediaRecorder;
      
      setIsRecording(true);
      setStatus('Recording...');
    } catch (error) {
      setStatus('Microphone access denied');
      console.error('Error starting recording:', error);
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    setIsRecording(false);
    setAudioLevel(0);
    setStatus(isConnected ? 'Connected' : 'Disconnected');
  };

  // Monitor audio level for visual feedback
  const monitorAudioLevel = () => {
    if (!analyserRef.current) return;
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    
    const updateLevel = () => {
      if (!analyserRef.current || !isRecording) return;
      
      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setAudioLevel(average);
      
      if (isRecording) {
        requestAnimationFrame(updateLevel);
      }
    };
    
    updateLevel();
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">
        AI Sales Audio Chat
      </h2>
      
      {/* Connection Status */}
      <div className="mb-4 p-3 rounded-lg bg-gray-50">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-600">Status:</span>
          <span className={`text-sm font-semibold ${
            isConnected ? 'text-green-600' : 'text-red-600'
          }`}>
            {status}
          </span>
        </div>
        <div className={`w-3 h-3 rounded-full mt-2 ${
          isConnected ? 'bg-green-500' : 'bg-red-500'
        }`}></div>
      </div>

      {/* Audio Level Indicator */}
      {isRecording && (
        <div className="mb-4">
          <div className="text-sm text-gray-600 mb-2">Audio Level:</div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-100"
              style={{ width: `${Math.min(audioLevel * 2, 100)}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Control Buttons */}
      <div className="space-y-3">
        {!isConnected ? (
          <button
            onClick={connectWebSocket}
            className="w-full py-3 px-4 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition-colors"
          >
            Connect to Server
          </button>
        ) : (
          <>
            {!isRecording ? (
              <button
                onClick={startRecording}
                className="w-full py-3 px-4 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-lg transition-colors"
              >
                🎤 Start Recording
              </button>
            ) : (
              <button
                onClick={stopRecording}
                className="w-full py-3 px-4 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg transition-colors"
              >
                ⏹️ Stop Recording
              </button>
            )}
            
            <button
              onClick={() => {
                wsRef.current?.close();
                setIsConnected(false);
              }}
              className="w-full py-2 px-4 bg-gray-500 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
            >
              Disconnect
            </button>
          </>
        )}
      </div>

      {/* Instructions */}
      <div className="mt-6 p-3 bg-blue-50 rounded-lg">
        <h3 className="text-sm font-semibold text-blue-800 mb-2">Instructions:</h3>
        <ul className="text-xs text-blue-700 space-y-1">
          <li>1. Click "Connect to Server" to establish WebSocket connection</li>
          <li>2. Click "Start Recording" to begin audio streaming</li>
          <li>3. Speak into your microphone</li>
          <li>4. Listen for AI responses through your speakers</li>
          <li>5. Click "Stop Recording" when done</li>
        </ul>
      </div>
    </div>
  );
}
