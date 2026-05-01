import { motion } from 'framer-motion';

export const LoadingSpinner = () => {
  return (
    <div className="flex items-center gap-2 p-4">
      <motion.div
        className="w-6 h-6 border-2 border-pokedex-red/30 border-t-pokedex-red rounded-full"
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      />
      <span className="text-glass-text text-sm">Consulting the database...</span>
    </div>
  );
};