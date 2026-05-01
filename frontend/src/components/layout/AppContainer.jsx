import { SplitPane } from './SplitPane';

export const AppContainer = ({ children }) => {
  const leftPanel = children.find(c => c.key === 'chat');
  const rightPanel = children.find(c => c.key === 'visor');

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f0f0f] via-[#1a1a2e] to-[#16213e]">
      <header className="border-b border-glass-border bg-glass/30 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-pokedex-red flex items-center justify-center shadow-lg shadow-pokedex-red/30">
            <span className="text-white font-bold text-lg">P</span>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            Agentic Pokédex
          </h1>
        </div>
      </header>

      <main className="h-[calc(100vh-73px)]">
        <SplitPane
          left={
            <div className="h-full">
              {leftPanel}
            </div>
          }
          right={
            <div className="h-full p-4 pl-0">
              {rightPanel}
            </div>
          }
        />
      </main>

      <div className="lg:hidden fixed bottom-0 left-0 right-0 p-4 bg-glass/80 backdrop-blur-md border-t border-glass-border">
        {children.find(c => c.key === 'mobile-visor')}
      </div>
    </div>
  );
};