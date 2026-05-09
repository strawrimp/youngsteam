import React from 'react';
import { useTheme } from '../hooks/useTheme';
import { useConversationStore } from '../store';

interface HeaderProps {
  status?: 'syncing' | 'synced' | 'offline';
  activeTab?: 'dashboard' | 'archive' | 'settings';
  onTabChange?: (tab: 'dashboard' | 'archive' | 'settings') => void;
  onMenuClick?: () => void;
  onNewConversation?: () => void;
}

const Header: React.FC<HeaderProps> = ({
  status = 'syncing',
  activeTab = 'dashboard',
  onTabChange,
  onMenuClick,
  onNewConversation,
}) => {
  useTheme(); // Keep import for theme initialization
  const currentReferenceCode = useConversationStore((s) => s.currentReferenceCode);

  const statusConfig = {
    syncing: {
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      border: 'border-emerald-100',
      label: '동기화 중',
      animate: true,
    },
    synced: {
      bg: 'bg-slate-50',
      text: 'text-slate-700',
      border: 'border-slate-100',
      label: '동기화 완료',
      animate: false,
    },
    offline: {
      bg: 'bg-slate-100',
      text: 'text-slate-600',
      border: 'border-slate-200',
      label: '오프라인',
      animate: false,
    },
  };

  const currentStatus = statusConfig[status];

  return (
    <header className={`
      flex justify-between items-center px-8 h-16 w-full 
      sticky top-0 z-50 border-b
      bg-white border-slate-100
    `}>
      {/* Left Side - Hamburger Menu (Mobile) & Status */}
      <div className="flex items-center gap-4">
        {/* Hamburger Menu - Mobile Only */}
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 rounded-lg transition-colors text-slate-600 hover:bg-slate-100 hover:text-primary"
          aria-label="메뉴 열기"
        >
          <span className="material-symbols-outlined">menu</span>
        </button>

        <div 
          className={`
            flex items-center gap-2 ${currentStatus.bg} ${currentStatus.text} 
            px-3 py-1 rounded-full text-xs font-bold border ${currentStatus.border}
          `}
        >
          <span 
            className={`w-2 h-2 rounded-full bg-current ${currentStatus.animate ? 'animate-pulse' : ''}`} 
          />
          {currentStatus.label}
        </div>

        {/* Reference Code Badge */}
        {currentReferenceCode && (
          <button
            onClick={() => navigator.clipboard.writeText(currentReferenceCode)}
            className="flex items-center gap-1 px-2 py-1 rounded-full text-xs font-mono font-bold border transition-colors bg-primary/10 text-primary border-primary/20 hover:bg-primary/20"
            title="클릭하여 참조 코드 복사"
          >
            <span className="material-symbols-outlined text-xs">tag</span>
            {currentReferenceCode}
          </button>
        )}
      </div>

      {/* Right Side - Tabs & Actions */}
      <div className="flex items-center gap-8">
        {/* Navigation Tabs */}
        <div className="hidden lg:flex items-center gap-8">
          <button
            onClick={() => onTabChange?.('dashboard')}
            className={`
              font-headline font-bold tracking-tight transition-all
              ${activeTab === 'dashboard'
                ? 'text-primary border-b-2 border-primary pb-1'
                : 'text-slate-500 hover:text-primary'
              }
            `}
          >
            대시보드
          </button>
          <button
            onClick={() => onTabChange?.('archive')}
            className={`
              font-headline font-bold tracking-tight transition-all
              ${activeTab === 'archive'
                ? 'text-primary border-b-2 border-primary pb-1'
                : 'text-slate-500 hover:text-primary'
              }
            `}
          >
            아카이브
          </button>
        </div>

        {/* Action Icons */}
        <div className="flex items-center gap-4 border-l pl-4 border-slate-100">
          {onNewConversation && (
            <button
              onClick={onNewConversation}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all
                bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20"
              title="새 대화 시작"
            >
              <span className="material-symbols-outlined text-sm">add_comment</span>
              새 대화
            </button>
          )}
          <button
            onClick={() => onTabChange?.('settings')}
            className="transition-colors text-slate-400 hover:text-primary"
          >
            <span className="material-symbols-outlined">settings</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
