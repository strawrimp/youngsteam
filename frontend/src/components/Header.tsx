import React from 'react';
import { useTheme } from '../hooks/useTheme';

interface HeaderProps {
  status?: 'syncing' | 'synced' | 'offline';
  activeTab?: 'dashboard' | 'archive' | 'settings';
  onTabChange?: (tab: 'dashboard' | 'archive' | 'settings') => void;
  onMenuClick?: () => void;
}

const Header: React.FC<HeaderProps> = ({
  status = 'syncing',
  activeTab = 'dashboard',
  onTabChange,
  onMenuClick,
}) => {
  const { theme, toggleTheme, isDark } = useTheme();

  const statusConfig = {
    syncing: {
      bg: isDark ? 'bg-emerald-900/30' : 'bg-emerald-50',
      text: isDark ? 'text-emerald-400' : 'text-emerald-700',
      border: isDark ? 'border-emerald-800' : 'border-emerald-100',
      label: '동기화 중',
      animate: true,
    },
    synced: {
      bg: isDark ? 'bg-blue-900/30' : 'bg-blue-50',
      text: isDark ? 'text-blue-400' : 'text-blue-700',
      border: isDark ? 'border-blue-800' : 'border-blue-100',
      label: '동기화 완료',
      animate: false,
    },
    offline: {
      bg: isDark ? 'bg-slate-800' : 'bg-slate-100',
      text: isDark ? 'text-slate-400' : 'text-slate-600',
      border: isDark ? 'border-slate-700' : 'border-slate-200',
      label: '오프라인',
      animate: false,
    },
  };

  const currentStatus = statusConfig[status];

  return (
    <header className={`
      flex justify-between items-center px-8 h-16 w-full 
      sticky top-0 z-50 border-b
      ${isDark 
        ? 'bg-slate-900 border-slate-800' 
        : 'bg-white border-slate-100'
      }
    `}>
      {/* Left Side - Hamburger Menu (Mobile) & Status */}
      <div className="flex items-center gap-4">
        {/* Hamburger Menu - Mobile Only */}
        <button
          onClick={onMenuClick}
          className={`
            md:hidden p-2 rounded-lg transition-colors
            ${isDark 
              ? 'text-slate-400 hover:bg-slate-800 hover:text-slate-200' 
              : 'text-slate-600 hover:bg-slate-100 hover:text-primary'
            }
          `}
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
                ? isDark 
                  ? 'text-blue-400 border-b-2 border-blue-400 pb-1'
                  : 'text-primary border-b-2 border-primary pb-1'
                : isDark
                  ? 'text-slate-400 hover:text-slate-200'
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
                ? isDark 
                  ? 'text-blue-400 border-b-2 border-blue-400 pb-1'
                  : 'text-primary border-b-2 border-primary pb-1'
                : isDark
                  ? 'text-slate-400 hover:text-slate-200'
                  : 'text-slate-500 hover:text-primary'
              }
            `}
          >
            아카이브
          </button>
        </div>

        {/* Action Icons */}
        <div className={`flex items-center gap-4 border-l pl-4 ${
          isDark ? 'border-slate-700' : 'border-slate-100'
        }`}>
          {/* Theme Toggle Button */}
          <button
            data-testid="theme-toggle"
            onClick={toggleTheme}
            className={`transition-colors ${
              isDark 
                ? 'text-slate-400 hover:text-yellow-400' 
                : 'text-slate-400 hover:text-amber-500'
            }`}
            title={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}
          >
              <span className="material-symbols-outlined">
                {isDark ? 'light_mode' : 'dark_mode'}
              </span>
            </button>

          <button className={`transition-colors ${
            isDark 
              ? 'text-slate-400 hover:text-slate-200' 
              : 'text-slate-400 hover:text-primary'
          }`}>
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button
            onClick={() => onTabChange?.('settings')}
            className={`transition-colors ${
              isDark
                ? 'text-slate-400 hover:text-slate-200'
                : 'text-slate-400 hover:text-primary'
            }`}
          >
            <span className="material-symbols-outlined">settings</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
