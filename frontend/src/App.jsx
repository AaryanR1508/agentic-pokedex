import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AppContainer } from './components/layout/AppContainer';
import { ChatWindow } from './components/chat/ChatWindow';
import { InputDock } from './components/chat/InputDock';
import { PokedexVisor } from './components/visor/PokedexVisor';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { usePokedexAPI } from './hooks/usePokedexAPI';

function App() {
  const [messages, setMessages] = useState([]);
  const [activeVisorData, setActiveVisorData] = useState(null);
  const [showMobileVisor, setShowMobileVisor] = useState(false);

  const { isRecording, audioBlob, error: audioError, toggleRecording, resetAudio } = useAudioRecorder();
  const { sendQuery, isLoading, error: apiError } = usePokedexAPI();

  useEffect(() => {
    if (audioBlob && !isRecording) {
      handleSendMessage({ audioBlob });
      resetAudio();
    }
  }, [audioBlob, isRecording]);

  const getTimestamp = () => {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleSendMessage = async ({ text, imageFile, audioBlob }) => {
    let userMessage = {};

    if (imageFile) {
      const imageUrl = URL.createObjectURL(imageFile);
      userMessage = {
        role: 'user',
        type: 'image',
        mediaUrl: imageUrl,
        content: text || 'Identify this Pokémon',
        timestamp: getTimestamp()
      };
    } else if (audioBlob) {
      userMessage = {
        role: 'user',
        type: 'audio',
        content: '🎤 Audio query',
        timestamp: getTimestamp()
      };
    } else {
      userMessage = {
        role: 'user',
        type: 'text',
        content: text,
        timestamp: getTimestamp()
      };
    }

    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await sendQuery({ text, imageFile, audioBlob });

      const aiMessage = {
        role: 'ai',
        type: 'text',
        content: response.response,
        timestamp: getTimestamp()
      };

      setMessages(prev => [...prev, aiMessage]);

      if (response.context_used) {
        setActiveVisorData(response.context_used);
        setShowMobileVisor(true);
      }
    } catch (error) {
      const errorMessage = {
        role: 'ai',
        type: 'text',
        content: apiError || 'Connection to the Pokédex network failed.',
        timestamp: getTimestamp()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const chatPanel = (
    <div className="h-full flex flex-col">
      <ChatWindow messages={messages} isTyping={isLoading} />
      <InputDock
        onSend={handleSendMessage}
        disabled={isLoading}
        isRecording={isRecording}
        onToggleRecording={toggleRecording}
        audioError={audioError}
      />
    </div>
  );

  const visorPanel = <PokedexVisor data={activeVisorData} />;

  return (
    <AppContainer>
      {[
        <div key="chat" className="h-full flex flex-col lg:flex-row">{chatPanel}</div>,
        <div key="visor">{visorPanel}</div>,
        <div key="mobile-visor">
          <AnimatePresence>
            {showMobileVisor && activeVisorData && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="max-h-64 overflow-y-auto"
              >
                <PokedexVisor data={activeVisorData} />
                <button
                  onClick={() => setShowMobileVisor(false)}
                  className="w-full py-2 text-sm text-gray-400 hover:text-white"
                >
                  Close
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ]}
    </AppContainer>
  );
}

export default App;