import React from 'react';
import { useConversationStore } from '../store';
import { getAgentConfig, getIconColorClass } from '../agentConfig';
import { useTheme } from '../hooks/useTheme';

interface MobileSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  activeAgentId?: string;
  onAgentSelect?: (agentId: string) => void;
}

const MobileSidebar: React.FC<MobileSidebarProps> = ({
  isOpen,
  onClose,
  activeAgentId = 'manager',
  onAgentSelect,
}) => {
  const agents = useConversationStore((state) => state.agents);
  const teamSettings = useConversationStore((state) => state.teamSettings);
  const { isDark } = useTheme();

  const handleAgentClick = (agentId: string) => {
    onAgentSelect?.(agentId);
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={`
          fixed inset-0 z-40 transition-opacity duration-300 md:hidden
          ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}
          ${isDark ? 'bg-black/60' : 'bg-black/40'}
        `}
        onClick={onClose}
      />

      {/* Sidebar Panel */}
      <div
        className={`
          fixed top-0 left-0 z-50 h-full w-[280px] transform transition-transform duration-300 ease-out md:hidden
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          ${isDark 
            ? 'bg-slate-900 border-r border-slate-800' 
            : 'bg-white border-r border-slate-200'
          }
        `}
      >
        {/* Logo Section */}
        <div className="p-6 border-b border-slate-200/30">
          <div className="flex items-center gap-3">
            <div className={`
              w-10 h-10 rounded-xl flex items-center justify-center
              ${isDark ? 'bg-blue-600 text-white' : 'bg-primary text-on-primary'}
            `}>
              <span className="material-symbols-outlined" style={{ fontVariationSettings: '"FILL" 1' }}>
                {teamSettings?.team_icon || 'terminal'}
              </span>
            </div>
            <div>
              <h2 className={`font-headline font-bold leading-tight ${
                isDark ? 'text-slate-100' : 'text-slate-900'
              }`}>
                {teamSettings?.team_name || "Young's Team"}
              </h2>
              <p className={`text-xs font-semibold tracking-wide ${
                isDark ? 'text-slate-500' : 'text-slate-500'
              }`}>
                {teamSettings?.team_subtitle || "AI Agents Online"}
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 flex flex-col gap-2 p-4 overflow-y-auto">
          {agents.map((agent) => {
            const isActive = agent.id === activeAgentId;
            const config = getAgentConfig(agent.id, agents);
            
            const getActiveClasses = () => {
              if (!isActive) {
                return isDark 
                  ? 'text-slate-400 hover:bg-slate-800'
                  : 'text-slate-500 hover:bg-slate-100';
              }
              
              switch (agent.role.toLowerCase()) {
                case 'manager':
                  return isDark 
                    ? 'bg-blue-900/40 text-blue-300' 
                    : 'bg-blue-50 text-blue-700';
                case 'developer':
                  return isDark 
                    ? 'bg-emerald-900/40 text-emerald-300' 
                    : 'bg-emerald-50 text-emerald-700';
                case 'designer':
                  return isDark 
                    ? 'bg-purple-900/40 text-purple-300' 
                    : 'bg-purple-50 text-purple-700';
                case 'researcher':
                  return isDark 
                    ? 'bg-amber-900/40 text-amber-300' 
                    : 'bg-amber-50 text-amber-700';
                default:
                  return isDark 
                    ? 'bg-slate-800 text-slate-200' 
                    : 'bg-slate-100 text-slate-700';
              }
            };
            
            return (
              <button
                key={agent.id}
                onClick={() => handleAgentClick(agent.id)}
                className={`
                  flex items-center gap-3 rounded-xl px-4 py-3
                  font-semibold tracking-wide transition-all duration-200
                  ${getActiveClasses()}
                `}
              >
                <span 
                  className={`material-symbols-outlined text-xl ${getIconColorClass(agent.role, isActive)}`}
                  style={{ fontVariationSettings: '"FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24' }}
                >
                  {config.icon}
                </span>
                <span className="text-lg">{config.display_name}</span>
              </button>
            );
          })}
        </nav>

      </div>
    </>
  );
};

export default MobileSidebar;
