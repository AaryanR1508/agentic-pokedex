import { motion } from 'framer-motion';

export const SplitPane = ({ left, right, leftWidth = '60%' }) => {
  return (
    <div className="flex h-full w-full">
      <motion.div
        className="h-full"
        style={{ width: leftWidth }}
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        {left}
      </motion.div>
      <motion.div
        className="h-full flex-1 hidden lg:block"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        {right}
      </motion.div>
    </div>
  );
};