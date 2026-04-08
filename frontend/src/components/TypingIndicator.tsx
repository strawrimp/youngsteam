import React from 'react';

interface TypingIndicatorProps {
  agentName?: string;
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({ agentName }) => {
  return (
    <div className="flex gap-4 items-center animate-fade-in">
      {/* Avatar Placeholder */}
      <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center 
                      flex-shrink-0 border border-slate-200">
        <span 
          className="material-symbols-outlined text-slate-500"
          style={{ fontVariationSettings: '"FILL" 1' }}
        >
          more_horiz
        </span>
      </div>

      {/* Typing Animation */}
      <div className="bg-white px-4 py-3 rounded-2xl border border-slate-200 shadow-sm flex gap-1">
        <div 
          className="w-2 h-2 rounded-full bg-slate-300 animate-typing-bounce"
          style={{ animationDelay: '0ms' }}
        />
        <div 
          className="w-2 h-2 rounded-full bg-slate-300 animate-typing-bounce"
          style={{ animationDelay: '150ms' }}
        />
        <div 
          className="w-2 h-2 rounded-full bg-slate-300 animate-typing-bounce"
          style={{ animationDelay: '300ms' }}
        />
      </div>

      {agentName && (
        <span className="text-xs text-slate-400 font-medium">
          {agentName}님이 입력 중...
        </span>
      )}
    </div>
  );
};

export default TypingIndicator;
