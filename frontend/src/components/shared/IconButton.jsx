import { motion } from 'framer-motion';

export const IconButton = ({ icon: Icon, onClick, disabled, tooltip, isActive, className = '' }) => {
  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      disabled={disabled}
      className={`
        p-3 rounded-xl transition-all duration-200
        ${disabled
          ? 'opacity-30 cursor-not-allowed'
          : 'hover:bg-white/10 cursor-pointer'
        }
        ${isActive
          ? 'bg-pokedex-red text-white shadow-lg shadow-pokedex-red/40'
          : 'text-gray-300 hover:text-white'
        }
        ${className}
      `}
      title={tooltip}
    >
      <Icon size={20} />
    </motion.button>
  );
};