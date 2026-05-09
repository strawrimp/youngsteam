import React from 'react';
import { useConversationStore } from '../store';
import { getAgentConfig, getRoleColorClass, getIconColorClass, getRoleTailwindClass } from '../agentConfig';
import { useTheme } from '../hooks/useTheme';

interface SidebarProps {
  activeAgentId?: string;
  onAgentSelect?: (agentId: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  activeAgentId = 'manager',
  onAgentSelect,
}) => {
  const agents = useConversationStore((state) => state.agents);
  const teamSettings = useConversationStore((state) => state.teamSettings);
  const { isDark } = useTheme();

  return (
    <aside className={`
      hidden md:flex flex-col gap-2 p-6 h-full w-sidebar border-r
      ${isDark 
        ? 'bg-slate-900 border-slate-800' 
        : 'bg-slate-50 border-slate-200/50'
      }
    `}>
      {/* Logo Section */}
      <div className="mb-8 flex items-center gap-3">
        <div className={`
          w-10 h-10 rounded-xl flex items-center justify-center
          ${isDark ? 'bg-slate-600 text-white' : 'bg-primary text-on-primary'}
        `}>
          <span className="material-symbols-outlined" style={{ fontVariationSettings: '"FILL" 1' }}>
            {teamSettings?.team_icon || 'terminal'}
          </span>
        </div>
        <div>
          <h2 className={`font-headline font-bold leading-tight ${
            isDark ? 'text-slate-100' : 'text-slate-900'
          }`}>
            {teamSettings?.team_name || "AI 경영진 팀"}
          </h2>
          <p className={`text-xs font-semibold tracking-wide ${
            isDark ? 'text-slate-500' : 'text-slate-500'
          }`}>
            {teamSettings?.team_subtitle || "다중 에이전트 협업 시스템"}
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-2">
        {agents.map((agent) => {
          const isActive = agent.id === activeAgentId;
          const config = getAgentConfig(agent.id, agents);
          
          // Dark mode aware color classes
          const getActiveClasses = () => {
            if (!isActive) {
              return isDark 
                ? 'text-slate-400 hover:translate-x-1 hover:bg-slate-800'
                : 'text-slate-500 hover:translate-x-1 hover:bg-slate-200/50';
            }
            
            return getRoleTailwindClass(agent.role.toLowerCase(), isDark);
          };
          
          return (
            <React.Fragment key={agent.id}>
              <button
                onClick={() => onAgentSelect?.(agent.id)}
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
                {agent.id === 'openclaw-bot' && (
                  <span
                    className={`inline-block w-2 h-2 rounded-full ml-auto flex-shrink-0 ${
                      agent.status === 'online' ? 'bg-emerald-500' : 'bg-slate-400'
                    }`}
                    title={agent.status === 'online' ? '온라인' : '오프라인'}
                  />
                )}
              </button>
              {isActive && config.description && (
                <p className={`text-[11px] leading-relaxed mt-1 px-4 pb-2 ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  {config.description}
                </p>
              )}
            </React.Fragment>
          );
        })}
      </nav>


    </aside>
  );
};

export default Sidebar;
