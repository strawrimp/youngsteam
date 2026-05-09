import React, { useState, useEffect, useCallback } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';
import { ArchivedConversation } from '../types';
import { useTheme } from '../hooks/useTheme';

const ConversationArchive: React.FC = () => {
  const { isDark } = useTheme();
  const [conversations, setConversations] = useState<ArchivedConversation[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // 참조 코드 복사 핸들러
  const handleCopyCode = useCallback((code: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(code).then(() => {
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 1500);
    });
  }, []);

  // Load conversations
  const loadConversations = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.getArchivedConversations(50, 0);
      setConversations(data.conversations);
    } catch (err) {
      console.error('[Archive] Failed to load:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // ★ 자동 갱신 — 백엔드에서 archive_updated WS 이벤트 수신 시
  useEffect(() => {
    const handleArchiveUpdate = () => {
      console.log('[Archive] Auto-refresh triggered');
      loadConversations();
    };
    window.addEventListener('archive_updated', handleArchiveUpdate);
    return () => window.removeEventListener('archive_updated', handleArchiveUpdate);
  }, [loadConversations]);

  // Search
  const handleSearch = useCallback(async (query: string) => {
    setSearchQuery(query);
    if (query.length < 2) {
      loadConversations();
      return;
    }
    setIsLoading(true);
    try {
      const data = await api.searchConversations(query);
      setConversations(data.conversations);
    } catch (err) {
      console.error('[Archive] Search failed:', err);
    } finally {
      setIsLoading(false);
    }
  }, [loadConversations]);

  // Delete conversation
  const handleDelete = useCallback(async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // prevent card selection toggle
    const conv = conversations.find(c => c.id === convId);
    const title = conv?.title || '이 대화';
    
    if (!window.confirm(`"${title}" 기록을 삭제하시겠습니까?\n삭제된 기록은 복구할 수 없습니다.`)) return;
    
    setDeletingId(convId);
    try {
      await api.deleteConversation(convId);
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (selectedId === convId) setSelectedId(null);
    } catch (err) {
      console.error('[Archive] Failed to delete:', err);
    } finally {
      setDeletingId(null);
    }
  }, [conversations, selectedId]);

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '방금 전';
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;
    return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };

  // Category colors
  const getCategoryColor = (category?: string) => {
    switch (category) {
      case '기획': return 'bg-blue-500/20 text-blue-400';
      case '개발': return 'bg-emerald-500/20 text-emerald-400';
      case '디자인': return 'bg-purple-500/20 text-purple-400';
      case '리서치': return 'bg-amber-500/20 text-amber-400';
      case '토론': return 'bg-rose-500/20 text-rose-400';
      case '의사결정': return 'bg-cyan-500/20 text-cyan-400';
      default: return isDark ? 'bg-slate-700/50 text-slate-400' : 'bg-slate-200 text-slate-600';
    }
  };

  return (
    <div className={`w-80 h-full flex flex-col overflow-hidden border-l ${
      isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
    }`}>
      {/* Header */}
      <div className={`p-4 border-b ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className={`text-sm font-bold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
            📚 대화 기록
          </h3>
          <button
            onClick={loadConversations}
            className={`p-1.5 rounded-lg transition-colors ${
              isDark ? 'hover:bg-slate-800 text-slate-500' : 'hover:bg-slate-100 text-slate-400'
            }`}
            title="새로고침"
          >
            <span className="material-symbols-outlined text-base">refresh</span>
          </button>
        </div>

        {/* Search */}
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${
          isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-slate-50 border-slate-200'
        }`}>
          <span className={`material-symbols-outlined text-base ${
            isDark ? 'text-slate-500' : 'text-slate-400'
          }`}>search</span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="대화 검색..."
            className={`flex-1 bg-transparent text-sm outline-none ${
              isDark ? 'text-slate-200 placeholder-slate-600' : 'text-slate-800 placeholder-slate-400'
            }`}
          />
          {searchQuery && (
            <button
              onClick={() => { setSearchQuery(''); loadConversations(); }}
              className={isDark ? 'text-slate-600 hover:text-slate-400' : 'text-slate-400 hover:text-slate-600'}
            >
              <span className="material-symbols-outlined text-base">close</span>
            </button>
          )}
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className={`flex items-center justify-center py-12 ${
            isDark ? 'text-slate-600' : 'text-slate-400'
          }`}>
            <div className="flex flex-col items-center gap-2">
              <span className="material-symbols-outlined animate-spin text-2xl">progress_activity</span>
              <span className="text-xs">불러오는 중...</span>
            </div>
          </div>
        ) : conversations.length === 0 ? (
          <div className={`flex flex-col items-center justify-center py-12 px-4 ${
            isDark ? 'text-slate-600' : 'text-slate-400'
          }`}>
            <span className="material-symbols-outlined text-3xl mb-2" style={{ fontVariationSettings: '"FILL" 0, "wght" 300' }}>
              forum
            </span>
            <p className="text-xs text-center">
              {searchQuery ? '검색 결과가 없습니다' : '아직 대화 기록이 없습니다'}
            </p>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => setSelectedId(selectedId === conv.id ? null : conv.id)}
                className={`group relative w-full text-left p-3 rounded-xl transition-all cursor-pointer ${
                  selectedId === conv.id
                    ? isDark
                      ? 'bg-slate-800 border border-slate-700'
                      : 'bg-slate-100 border border-slate-200'
                    : isDark
                      ? 'hover:bg-slate-800/50'
                      : 'hover:bg-slate-50'
                }`}
              >
                {/* Delete button — appears on hover */}
                <button
                  onClick={(e) => handleDelete(conv.id, e)}
                  disabled={deletingId === conv.id}
                  className={`absolute top-2 right-2 p-1 rounded-md opacity-0 group-hover:opacity-100
                             transition-all z-10 ${
                    deletingId === conv.id
                      ? 'opacity-100'
                      : isDark
                        ? 'hover:bg-red-900/30 text-slate-600 hover:text-red-400'
                        : 'hover:bg-red-50 text-slate-400 hover:text-red-500'
                  }`}
                  title="대화 삭제"
                >
                  <span className={`material-symbols-outlined text-sm ${
                    deletingId === conv.id ? 'animate-spin' : ''
                  }`}>
                    {deletingId === conv.id ? 'progress_activity' : 'delete'}
                  </span>
                </button>

                {/* Title row */}
                <div className="flex items-start gap-2 mb-1.5">
                  <span className="material-symbols-outlined text-sm mt-0.5 flex-shrink-0" style={{ fontVariationSettings: '"FILL" 0, "wght" 300' }}>
                    chat_bubble
                  </span>
                  <span className={`text-sm font-medium line-clamp-1 flex-1 pr-6 ${
                    isDark ? 'text-slate-200' : 'text-slate-800'
                  }`}>
                    {conv.title || '제목 없는 대화'}
                  </span>
                </div>

                {/* Reference code + Meta row */}
                <div className="flex items-center gap-2 pl-5">
                  {conv.reference_code && (
                    <>
                      <span
                        className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded cursor-pointer transition-all duration-200 ${
                          copiedCode === conv.reference_code
                            ? 'bg-emerald-500/20 text-emerald-400 scale-105'
                            : isDark
                              ? 'bg-primary/20 text-primary hover:bg-primary/30 active:scale-95'
                              : 'bg-primary/10 text-primary hover:bg-primary/20 active:scale-95'
                        }`}
                        title="클릭하여 복사"
                        onClick={(e) => handleCopyCode(conv.reference_code!, e)}
                      >
                        {copiedCode === conv.reference_code ? '✓ 복사됨' : conv.reference_code}
                      </span>
                      <span className={`text-[10px] ${isDark ? 'text-slate-600' : 'text-slate-300'}`}>•</span>
                    </>
                  )}
                  <span className={`text-[10px] ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {formatDate(conv.started_at)}
                  </span>
                  <span className={`text-[10px] ${isDark ? 'text-slate-600' : 'text-slate-300'}`}>•</span>
                  <span className={`text-[10px] ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {conv.message_count}개 메시지
                  </span>
                  {conv.category && (
                    <>
                      <span className={`text-[10px] ${isDark ? 'text-slate-600' : 'text-slate-300'}`}>•</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${getCategoryColor(conv.category)}`}>
                        {conv.category}
                      </span>
                    </>
                  )}
                </div>

                {/* Tags */}
                {conv.tags && conv.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5 pl-5">
                    {conv.tags.slice(0, 3).map((tag, idx) => (
                      <span
                        key={idx}
                        className={`text-[9px] px-1.5 py-0.5 rounded ${
                          isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Expanded detail */}
                {selectedId === conv.id && conv.summary && (
                  <div className={`mt-2 p-2 rounded-lg text-xs leading-relaxed ${
                    isDark ? 'bg-slate-800/50 text-slate-400' : 'bg-slate-50 text-slate-600'
                  }`}>
                    {conv.summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className={`p-3 border-t text-center ${
        isDark ? 'border-slate-800' : 'border-slate-200'
      }`}>
        <span className={`text-[10px] ${isDark ? 'text-slate-600' : 'text-slate-400'}`}>
          총 {conversations.length}개의 대화 기록
        </span>
      </div>
    </div>
  );
};

export default ConversationArchive;
