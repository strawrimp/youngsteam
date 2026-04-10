import React from 'react';
import { useConversationStore } from '../store';
import { getAgentConfig } from '../agentConfig';
import { useTheme } from '../hooks/useTheme';

export type MessageRole = 'manager' | 'developer' | 'designer' | 'researcher' | 'user';

export interface MessageBubbleProps {
  role: MessageRole;
  name: string;
  content: string;
  timestamp?: string;
  isCode?: boolean;
  isUser?: boolean;
  showRoleBadge?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  role,
  name,
  content,
  timestamp,
  isCode = false,
  isUser = false,
  showRoleBadge = true,
}) => {
  const agents = useConversationStore((state) => state.agents);
  const { isDark } = useTheme();
  
  // role로 에이전트 찾기
  const agent = agents.find(a => a.role === role);
  const config = getAgentConfig(role, agents);

  if (isUser) {
    return (
      <div className="flex gap-4 max-w-2xl ml-auto animate-fade-in-up">
        {/* Avatar */}
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg ${
          isDark ? 'bg-slate-600 shadow-slate-500/30' : 'bg-primary shadow-primary/20'
        }`}>
          <span 
            className="material-symbols-outlined text-white" 
            style={{ fontVariationSettings: '"FILL" 1' }}
          >
            person
          </span>
        </div>

        {/* Message Content */}
        <div className="flex flex-col gap-2 items-end">
          <div className="flex items-center gap-2">
            <span className={`font-headline font-bold text-xl ${
              isDark ? 'text-slate-100' : 'text-slate-900'
            }`}>
              나
            </span>
          </div>
          <div className={`p-5 rounded-2xl rounded-tr-2xl rounded-br-sm ${
            isDark ? 'bg-slate-600' : 'bg-primary'
          } text-white`}>
            <p className="text-base">
              {content}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4 max-w-2xl animate-fade-in-up">
      {/* Avatar */}
      <div 
        className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg`}
        style={{ backgroundColor: config.color }}
      >
        <span 
          className="material-symbols-outlined text-white" 
          style={{ fontVariationSettings: '"FILL" 1' }}
        >
          {config.icon}
        </span>
      </div>

      {/* Message Content */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className={`font-headline font-bold text-xl ${
            isDark ? 'text-slate-100' : 'text-slate-900'
          }`}>
            {name}
          </span>
          {showRoleBadge && config.badge_text && (
            <span 
              className="text-[10px] text-white px-2 py-0.5 rounded-md font-bold uppercase tracking-tighter"
              style={{ backgroundColor: config.color }}
            >
              {config.badge_text}
            </span>
          )}
        </div>
        
        {isCode ? (
          <div className={`p-5 rounded-2xl rounded-tl-none border shadow-sm
                       font-mono text-sm leading-relaxed ${
            isDark 
              ? 'bg-slate-800 border-slate-700 text-slate-200' 
              : 'bg-slate-900 border-slate-800 text-slate-200'
          }`}>
            {content}
          </div>
        ) : (
          <div 
            className={`p-5 rounded-2xl rounded-tl-none shadow-sm text-base leading-relaxed ${
              isDark ? 'text-on-surface' : 'text-on-surface'
            }`}
            style={{ 
              backgroundColor: `${config.color}15`,
              borderLeft: `3px solid ${config.color}`
            }}
          >
            {content}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
