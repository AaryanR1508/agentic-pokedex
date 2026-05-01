const TYPE_COLORS = {
  normal: 'bg-stone-400',
  fire: 'bg-orange-500',
  water: 'bg-blue-500',
  electric: 'bg-yellow-400',
  grass: 'bg-green-500',
  ice: 'bg-cyan-300',
  fighting: 'bg-red-700',
  poison: 'bg-purple-500',
  ground: 'bg-amber-600',
  flying: 'bg-sky-400',
  psychic: 'bg-pink-500',
  bug: 'bg-lime-500',
  rock: 'bg-stone-500',
  ghost: 'bg-indigo-700',
  dragon: 'bg-indigo-600',
  dark: 'bg-gray-700',
  steel: 'bg-slate-400',
  fairy: 'bg-pink-300',
};

export const TypeBadge = ({ type }) => {
  const colorClass = TYPE_COLORS[type?.toLowerCase()] || 'bg-gray-500';

  return (
    <span
      className={`
        inline-block px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider
        ${colorClass} text-white shadow-md
      `}
    >
      {type}
    </span>
  );
};