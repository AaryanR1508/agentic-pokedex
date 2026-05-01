import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Camera, Mic, MicOff, X, ImageIcon } from 'lucide-react';
import { IconButton } from '../shared/IconButton';

export const InputDock = ({ onSend, disabled, isRecording, onToggleRecording, audioError }) => {
  const [text, setText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const fileInputRef = useRef(null);

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      alert('Image must be less than 5MB');
      return;
    }

    setSelectedImage(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleSubmit = () => {
    if (!text.trim() && !selectedImage) return;

    onSend({
      text: text.trim() || null,
      imageFile: selectedImage
    });

    setText('');
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="p-4 border-t border-glass-border bg-glass/50 backdrop-blur-md">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg"
        onChange={handleImageSelect}
        className="hidden"
      />

      <AnimatePresence>
        {imagePreview && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3"
          >
            <div className="relative inline-block">
              <img
                src={imagePreview}
                alt="Preview"
                className="max-h-32 rounded-lg border border-pokedex-red/30"
              />
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

      <div className="flex items-center gap-2">
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

        <div className="flex-1">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? 'Processing...' : 'Ask about any Pokémon...'}
            disabled={disabled}
            className="w-full px-4 py-3 rounded-xl bg-white/5 border border-glass-border text-white placeholder-gray-500 focus:outline-none focus:border-pokedex-red/50 focus:ring-1 focus:ring-pokedex-red/30 transition-all"
          />
        </div>

        <IconButton
          icon={Send}
          onClick={handleSubmit}
          disabled={disabled || (!text.trim() && !selectedImage)}
          tooltip="Send message"
          isActive={text.trim() || selectedImage}
        />
      </div>

      <div className="mt-3 flex justify-center">
        <p className="text-xs text-gray-500">
          Tip: Upload an image or use the microphone to identify Pokémon
        </p>
      </div>
    </div>
  );
};