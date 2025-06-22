import AudioStreamer from '@/components/AudioStreamer';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="container mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            AI Sales Assistant
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Connect with our AI-powered sales assistant through real-time voice conversation. 
            Start by connecting to the server and begin your audio chat session.
          </p>
        </div>
        
        <AudioStreamer 
          serverUrl="ws://localhost:8000"
          clientId={`client_${Date.now()}`}
        />
        
        <div className="mt-12 text-center">
          <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-2xl mb-3">🎤</div>
              <h3 className="font-semibold text-gray-800 mb-2">Voice Input</h3>
              <p className="text-sm text-gray-600">
                Speak naturally to interact with the AI assistant using your microphone
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-2xl mb-3">🤖</div>
              <h3 className="font-semibold text-gray-800 mb-2">AI Processing</h3>
              <p className="text-sm text-gray-600">
                Powered by Google's Gemini Live API for natural conversation
              </p>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-2xl mb-3">🔊</div>
              <h3 className="font-semibold text-gray-800 mb-2">Audio Response</h3>
              <p className="text-sm text-gray-600">
                Receive real-time audio responses from the AI assistant
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
