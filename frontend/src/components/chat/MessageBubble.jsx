import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

export const MessageBubble = ({ message, index }) => {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
    >
      <div
        className={`
          max-w-[80%] rounded-2xl px-4 py-3
          ${isUser
            ? 'bg-pokedex-red text-white rounded-br-md'
            : 'glass-strong text-gray-100 rounded-bl-md'
          }
        `}
      >
        {message.type === 'image' && message.mediaUrl && (
          <div className="mb-2">
            <img
              src={message.mediaUrl}
              alt="Uploaded"
              className="max-w-full rounded-lg border border-white/20"
            />
          </div>
        )}

        {message.type === 'audio' && (
          <div className="flex items-center gap-2 mb-2 text-sm text-white/80">
            <span className="text-xs">🎤 Audio message</span>
          </div>
        )}

        {message.content && (
          <div className={`text-sm leading-relaxed ${isUser ? 'text-white' : 'text-gray-100'}`}>
            {isUser ? (
              <p>{message.content}</p>
            ) : (
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-2">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
                  li: ({ children }) => <li className="mb-1">{children}</li>,
                  strong: ({ children }) => <strong className="text-pokedex-redLight font-semibold">{children}</strong>,
                  code: ({ children }) => <code className="bg-white/10 px-1 py-0.5 rounded text-pokedex-redLight">{children}</code>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>
        )}

        <div className={`text-xs mt-1 ${isUser ? 'text-white/60' : 'text-gray-500'}`}>
          {message.timestamp || ''}
        </div>
      </div>
    </motion.div>
  );
};