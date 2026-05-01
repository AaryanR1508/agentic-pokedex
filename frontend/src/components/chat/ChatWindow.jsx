import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { LoadingSpinner } from '../shared/LoadingSpinner';

export const ChatWindow = ({ messages, isTyping }) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex-1 overflow-y-auto pr-2">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="text-6xl mb-4">⚡</div>
            <h2 className="text-2xl font-bold text-white mb-2">Welcome to the Pokédex</h2>
            <p className="text-gray-400 max-w-md">
              Ask me about any Pokémon, upload an image to identify it, or record audio to hear their cry!
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <MessageBubble key={idx} message={msg} index={idx} />
          ))
        )}

        {isTyping && <LoadingSpinner />}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};