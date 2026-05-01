import { motion } from 'framer-motion';

const STAT_COLORS = {
  hp: 'bg-green-500',
  attack: 'bg-red-500',
  defense: 'bg-yellow-500',
  'sp-atk': 'bg-blue-500',
  'sp-def': 'bg-purple-500',
  speed: 'bg-cyan-400',
};

const STAT_NAMES = {
  hp: 'HP',
  attack: 'ATK',
  defense: 'DEF',
  'sp-atk': 'SP.A',
  'sp-def': 'SP.D',
  speed: 'SPD',
};

const MAX_STAT = 255;

export const StatBar = ({ statName, value }) => {
  const percentage = Math.min((value / MAX_STAT) * 100, 100);
  const colorClass = STAT_COLORS[statName] || 'bg-gray-500';
  const displayName = STAT_NAMES[statName] || statName;

  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="text-xs text-gray-400 w-10 uppercase">{displayName}</span>
      <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${colorClass} rounded-full`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs text-gray-300 w-6 text-right font-mono">{value}</span>
    </div>
  );
};