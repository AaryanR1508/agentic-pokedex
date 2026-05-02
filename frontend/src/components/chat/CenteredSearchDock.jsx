import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Mic, MicOff, X, ImageIcon } from 'lucide-react';
import { IconButton } from '../shared/IconButton';

/**
 * A landing-screen search bar.
 * Shares the same onSend API as InputDock so App.jsx can call both the same way.
 */
export const CenteredSearchDock = ({ onSend, disabled, isRecording, onToggleRecording, audioError }) => {
  const [text, setText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const fileInputRef = useRef(null);

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { alert('Image must be less than 5MB'); return; }
    setSelectedImage(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleSubmit = () => {
    if (!text.trim() && !selectedImage) return;
    onSend({ text: text.trim() || null, imageFile: selectedImage });
    setText('');
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg"
        onChange={handleImageSelect}
        className="hidden"
      />

      {/* Image preview */}
      <AnimatePresence>
        {imagePreview && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3"
          >
            <div className="relative inline-block">
              <img src={imagePreview} alt="Preview" className="max-h-32 rounded-lg border border-pokedex-red/30" />
              <button
                onClick={clearImage}
                className="absolute -top-2 -right-2 bg-pokedex-red text-white rounded-full p-1 hover:bg-pokedex-redDark transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search row */}
      <div className="flex items-center gap-3 glass-strong rounded-2xl px-3 py-2 shadow-xl shadow-black/40 ring-1 ring-pokedex-red/20 focus-within:ring-pokedex-red/50 transition-all">
        <IconButton
          icon={ImageIcon}
          onClick={() => fileInputRef.current?.click()}
          tooltip="Upload image"
          disabled={disabled}
        />
        <IconButton
          icon={isRecording ? MicOff : Mic}
          onClick={onToggleRecording}
          tooltip={audioError || (isRecording ? 'Stop recording' : 'Start recording')}
          disabled={disabled || !!audioError}
          isActive={isRecording}
          className={isRecording ? 'animate-pulse' : ''}
        />

        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Processing...' : 'Ask about any Pokémon…'}
          disabled={disabled}
          className="flex-1 bg-transparent text-white placeholder-gray-500 focus:outline-none text-base py-2"
        />

        <IconButton
          icon={Send}
          onClick={handleSubmit}
          disabled={disabled || (!text.trim() && !selectedImage)}
          tooltip="Send"
          isActive={!!(text.trim() || selectedImage)}
        />
      </div>

      <p className="text-center text-xs text-gray-600 mt-3">
        Tip: upload an image or use the mic to identify Pokémon
      </p>
    </div>
  );
};
