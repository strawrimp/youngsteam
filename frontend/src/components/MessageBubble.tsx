import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useConversationStore } from '../store';
import { getAgentConfig } from '../agentConfig';
import { useTheme } from '../hooks/useTheme';
import { ReplyInfo } from '../types';

export type MessageRole = 'manager' | 'developer' | 'designer' | 'researcher' | 'user';

export interface MessageBubbleProps {
  role: MessageRole;
  name: string;
  content: string;
  timestamp?: string;
  isCode?: boolean;
  isUser?: boolean;
  showRoleBadge?: boolean;
  messageId?: string;
  replyTo?: ReplyInfo;
  onReply?: () => void;
  imageUrl?: string;
}

const truncateText = (text: string, maxLen: number = 30) => {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + '...';
};

const MessageBubble: React.FC<MessageBubbleProps> = ({
  role,
  name,
  content,
  timestamp,
  isCode = false,
  isUser = false,
  showRoleBadge = true,
  messageId,
  replyTo,
  onReply,
  imageUrl,
}) => {
  const agents = useConversationStore((state) => state.agents);
  const { isDark } = useTheme();
  
  // role로 에이전트 찾기
  const agent = agents.find(a => a.role === role);
  const config = getAgentConfig(role, agents);

  // 답장 원본 메시지의 색상 가져오기
  const replyConfig = replyTo ? getAgentConfig(replyTo.role, agents) : null;

  // 인용구 UI
  const ReplyQuote: React.FC<{ quote: ReplyInfo }> = ({ quote }) => {
    const qConfig = getAgentConfig(quote.role, agents);
    return (
      <div 
        className="flex items-center gap-1.5 px-2 py-1 mb-1 rounded-lg cursor-pointer hover:brightness-95 transition-all"
        style={{ 
          backgroundColor: `${qConfig.color}10`,
          borderLeft: `2px solid ${qConfig.color}`
        }}
        onClick={(e) => {
          e.stopPropagation();
          // 원본 메시지로 스크롤
          const el = document.getElementById(`msg-${quote.id}`);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('ring-2', 'ring-blue-400/50');
            setTimeout(() => el.classList.remove('ring-2', 'ring-blue-400/50'), 1500);
          }
        }}
      >
        <div 
          className="w-3.5 h-3.5 rounded flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: qConfig.color }}
        >
          <span className="material-symbols-outlined text-white" style={{ fontSize: '8px', fontVariationSettings: '"FILL" 1' }}>
            {qConfig.icon}
          </span>
        </div>
        <span 
          className="text-[10px] font-bold flex-shrink-0"
          style={{ color: qConfig.color }}
        >
          {quote.name}
        </span>
        <span className={`text-[10px] truncate ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
          {truncateText(quote.content, 40)}
        </span>
      </div>
    );
  };

  if (isUser) {
    return (
      <div id={`msg-${messageId}`} data-is-user="true" className="group relative flex max-w-2xl ml-auto animate-fade-in-up">
        {/* Reply button — appears on hover */}
        {onReply && (
          <button
            onClick={onReply}
            className={`absolute -left-8 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 
                       transition-opacity p-1 rounded-md ${
              isDark 
                ? 'hover:bg-slate-700 text-slate-500' 
                : 'hover:bg-slate-100 text-slate-400'
            }`}
            title="답장"
          >
            <span className="material-symbols-outlined text-sm">reply</span>
          </button>
        )}
        {/* Message Content */}
        <div className="flex flex-col gap-0.5 items-end">
          {replyTo && <ReplyQuote quote={replyTo} />}
          {/* ★ 이미지 표시 */}
          {imageUrl && (
            <div className="max-w-xs overflow-hidden rounded-2xl rounded-tr-sm">
              <img
                src={imageUrl}
                alt="첨부 이미지"
                className="w-full h-auto max-h-80 object-cover cursor-pointer hover:brightness-95 transition-all"
                onClick={() => {
                  // 이미지 확대 모달
                  const overlay = document.createElement('div');
                  overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
                  overlay.onclick = () => overlay.remove();
                  const img = document.createElement('img');
                  img.src = imageUrl;
                  img.style.cssText = 'max-width:90vw;max-height:90vh;object-fit:contain;border-radius:8px;';
                  overlay.appendChild(img);
                  document.body.appendChild(overlay);
                }}
              />
            </div>
          )}
          {/* 텍스트 내용 — 이미지만 있고 텍스트가 "(이미지)"면 숨김 */}
          {!(imageUrl && (content === '(이미지)' || content === '')) && (
            <div className={`px-3 py-2 rounded-2xl ${
              imageUrl ? 'rounded-tr-sm mt-0.5' : 'rounded-tr-sm'
            } ${isDark ? 'bg-slate-600' : 'bg-primary'}`}>
              <p className="text-sm whitespace-pre-wrap leading-snug text-white">
                {content}
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div id={`msg-${messageId}`} className="group relative flex gap-2 max-w-2xl animate-fade-in-up">
      {/* Avatar */}
      <div 
        className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0`}
        style={{ backgroundColor: config.color }}
      >
        <span 
          className="material-symbols-outlined text-white text-sm" 
          style={{ fontVariationSettings: '"FILL" 1' }}
        >
          {config.icon}
        </span>
      </div>

      {/* Message Content */}
      <div className="flex flex-col gap-0.5 flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className={`font-headline font-semibold text-xs ${
            isDark ? 'text-slate-400' : 'text-slate-500'
          }`}>
            {name}
          </span>
          {showRoleBadge && config.badge_text && (
            <span 
              className="text-[9px] text-white px-1.5 py-px rounded font-bold uppercase tracking-tighter"
              style={{ backgroundColor: config.color }}
            >
              {config.badge_text}
            </span>
          )}
          {/* Reply button — appears on hover */}
          {onReply && (
            <button
              onClick={onReply}
              className={`opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded ${
                isDark 
                  ? 'hover:bg-slate-700 text-slate-500 hover:text-slate-300' 
                  : 'hover:bg-slate-100 text-slate-400 hover:text-slate-600'
              }`}
              title="답장"
            >
              <span className="material-symbols-outlined text-xs">reply</span>
            </button>
          )}
        </div>
        
        {isCode ? (
          <>
            {replyTo && <ReplyQuote quote={replyTo} />}
            <div className={`px-3 py-2 rounded-2xl rounded-tl-none border
                         font-mono text-xs leading-relaxed ${
              isDark 
                ? 'bg-slate-800 border-slate-700 text-slate-200' 
                : 'bg-slate-900 border-slate-800 text-slate-200'
            }`}>
              <pre className="whitespace-pre-wrap">{content}</pre>
            </div>
          </>
        ) : (
          <>
            {replyTo && <ReplyQuote quote={replyTo} />}
            <div 
              className={`px-3 py-2 rounded-2xl rounded-tl-none text-sm leading-snug ${
                isDark ? 'text-on-surface' : 'text-on-surface'
              }`}
              style={{ 
                backgroundColor: `${config.color}12`,
                borderLeft: `2px solid ${config.color}`
              }}
            >
              <div className="markdown-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    a: ({ href, children, ...props }) => (
                      <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
                        {children}
                      </a>
                    ),
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
