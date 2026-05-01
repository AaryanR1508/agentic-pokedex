import { motion, AnimatePresence } from 'framer-motion';
import { TypeBadge } from './TypeBadge';
import { StatBar } from './StatBar';

const TYPE_GLOW_COLORS = {
  fire: 'shadow-[0_0_40px_rgba(249,115,22,0.4)]',
  water: 'shadow-[0_0_40px_rgba(59,130,246,0.4)]',
  electric: 'shadow-[0_0_40px_rgba(250,204,21,0.4)]',
  grass: 'shadow-[0_0_40px_rgba(34,197,94,0.4)]',
  ice: 'shadow-[0_0_40px_rgba(103,232,249,0.4)]',
  fighting: 'shadow-[0_0_40px_rgba(153,27,27,0.4)]',
  poison: 'shadow-[0_0_40px_rgba(168,85,247,0.4)]',
  ground: 'shadow-[0_0_40px_rgba(217,119,6,0.4)]',
  flying: 'shadow-[0_0_40px_rgba(14,165,233,0.4)]',
  psychic: 'shadow-[0_0_40px_rgba(236,72,153,0.4)]',
  bug: 'shadow-[0_0_40px_rgba(132,204,22,0.4)]',
  rock: 'shadow-[0_0_40px_rgba(120,113,114,0.4)]',
  ghost: 'shadow-[0_0_40px_rgba(79,70,229,0.4)]',
  dragon: 'shadow-[0_0_40px_rgba(79,70,229,0.4)]',
  dark: 'shadow-[0_0_40px_rgba(55,65,81,0.4)]',
  steel: 'shadow-[0_0_40px_rgba(161,161,170,0.4)]',
  fairy: 'shadow-[0_0_40px_rgba(249,168,212,0.4)]',
  normal: 'shadow-[0_0_40px_rgba(168,162,158,0.4)]',
};

export const PokedexVisor = ({ data }) => {
  const hasData = data && data.pokemon_name;

  return (
    <div className="h-full flex items-center justify-center p-4">
      <AnimatePresence mode="wait">
        {hasData ? (
          <motion.div
            key={data.pokemon_name}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className={`
              w-full max-w-md glass-strong rounded-3xl overflow-hidden
              ${TYPE_GLOW_COLORS[data.types?.[0]?.toLowerCase()] || 'shadow-[0_0_40px_rgba(238,21,21,0.3)]'}
              scanline
            `}
          >
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-white capitalize">
                    {data.pokemon_name}
                  </h2>
                  <span className="text-sm text-gray-400">
                    #{String(data.pokemon_id || 0).padStart(3, '0')}
                  </span>
                </div>
                <div className="flex gap-2">
                  {data.types?.map((type, idx) => (
                    <TypeBadge key={idx} type={type} />
                  ))}
                </div>
              </div>

              <div className="flex justify-center mb-6">
                <div className="relative">
                  <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="w-40 h-40 rounded-full bg-white/10 flex items-center justify-center"
                  >
                    {data.sprite_url ? (
                      <img
                        src={data.sprite_url}
                        alt={data.pokemon_name}
                        className="w-32 h-32 object-contain drop-shadow-lg"
                      />
                    ) : (
                      <span className="text-6xl">❓</span>
                    )}
                  </motion.div>
                </div>
              </div>

              {data.stats && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                    Base Stats
                  </h3>
                  {Object.entries(data.stats).map(([stat, value]) => (
                    <StatBar key={stat} statName={stat} value={value} />
                  ))}
                </div>
              )}

              {data.flavor_text && (
                <div className="mb-4">
                  <p className="text-sm text-gray-300 italic leading-relaxed">
                    "{data.flavor_text}"
                  </p>
                </div>
              )}

              {data.graph_relationships && data.graph_relationships.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
                    Data
                  </h3>
                  <div className="space-y-1">
                    {data.graph_relationships.map((rel, idx) => (
                      <p key={idx} className="text-xs text-gray-400">
                        {rel}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center p-8"
          >
            <div className="text-6xl mb-4 opacity-30">📡</div>
            <p className="text-gray-500">Searching database...</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};