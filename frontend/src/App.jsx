import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChatWindow } from './components/chat/ChatWindow';
import { InputDock } from './components/chat/InputDock';
import { CenteredSearchDock } from './components/chat/CenteredSearchDock';
import { PokedexVisor } from './components/visor/PokedexVisor';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { usePokedexAPI } from './hooks/usePokedexAPI';

function App() {
  const [messages, setMessages] = useState([]);
  const [activeVisorData, setActiveVisorData] = useState(null);
  // true once the user has sent at least one message
  const [hasStarted, setHasStarted] = useState(false);

  const { isRecording, audioBlob, error: audioError, toggleRecording, resetAudio } = useAudioRecorder();
  const { sendQuery, isLoading, error: apiError } = usePokedexAPI();

  useEffect(() => {
    if (audioBlob && !isRecording) {
      handleSendMessage({ audioBlob });
      resetAudio();
    }
  }, [audioBlob, isRecording]);

  const getTimestamp = () =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const handleSendMessage = async ({ text, imageFile, audioBlob }) => {
    setHasStarted(true);

    let userMessage = {};
    if (imageFile) {
      const imageUrl = URL.createObjectURL(imageFile);
      userMessage = { role: 'user', type: 'image', mediaUrl: imageUrl, content: text || 'Identify this Pokémon', timestamp: getTimestamp() };
    } else if (audioBlob) {
      userMessage = { role: 'user', type: 'audio', content: '🎤 Audio query', timestamp: getTimestamp() };
    } else {
      userMessage = { role: 'user', type: 'text', content: text, timestamp: getTimestamp() };
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

  return (
    <div className="h-screen bg-gradient-to-br from-[#0f0f0f] via-[#1a1a2e] to-[#16213e] flex flex-col overflow-hidden">
      {/* Header */}
      <header className="border-b border-glass-border bg-glass/30 backdrop-blur-md sticky top-0 z-50 flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-pokedex-red flex items-center justify-center shadow-lg shadow-pokedex-red/30">
            <span className="text-white font-bold text-lg">P</span>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">Agentic Pokédex</h1>
        </div>
      </header>

      {/* Main content area */}
      <main className="flex-1 flex min-h-0">
        <AnimatePresence mode="wait">
          {!hasStarted ? (
            /* ── Landing: centered search bar ── */
            <motion.div
              key="landing"
              className="flex-1 flex flex-col items-center justify-center px-4"
              initial={{ opacity: 1 }}
              exit={{ opacity: 0, y: -30 }}
              transition={{ duration: 0.35 }}
            >
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="text-center mb-10"
              >
                <div className="text-7xl mb-5">⚡</div>
                <h2 className="text-3xl font-bold text-white mb-3">Welcome to the Pokédex</h2>
                <p className="text-gray-400 max-w-md text-base">
                  Ask me about any Pokémon, upload an image to identify it, or record audio to hear their cry!
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="w-full max-w-2xl"
              >
                <CenteredSearchDock
                  onSend={handleSendMessage}
                  disabled={isLoading}
                  isRecording={isRecording}
                  onToggleRecording={toggleRecording}
                  audioError={audioError}
                />
              </motion.div>
            </motion.div>
          ) : (
            /* ── Active: split layout ── */
            <motion.div
              key="split"
              className="flex-1 flex min-h-0 overflow-hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
            >
              {/* Chat panel */}
              <motion.div
                className="flex flex-col min-h-0"
                style={{ width: '60%' }}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35 }}
              >
                <ChatWindow messages={messages} isTyping={isLoading} />
                <InputDock
                  onSend={handleSendMessage}
                  disabled={isLoading}
                  isRecording={isRecording}
                  onToggleRecording={toggleRecording}
                  audioError={audioError}
                />
              </motion.div>

              {/* Visor panel */}
              <motion.div
                className="flex-1 hidden lg:flex min-h-0 p-4 pl-0"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, delay: 0.1 }}
              >
                <PokedexVisor data={activeVisorData} isSearching={isLoading} />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;