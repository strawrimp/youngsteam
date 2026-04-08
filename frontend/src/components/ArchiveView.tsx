import React, { useState, useEffect } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';
import { ArchivedConversation, ConversationDetail } from '../types';
import MessageBubble from './MessageBubble';

const ArchiveView: React.FC = () => {
  const {
    archiveConversations,
    selectedConversation,
    archiveLoading,
    setActiveTab,
    setArchiveConversations,
    setSelectedConversation,
    setArchiveLoading,
  } = useConversationStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ArchivedConversation[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    setArchiveLoading(true);
    try {
      const response = await api.getArchivedConversations(50, 0);
      setArchiveConversations(response.conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setArchiveLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() || searchQuery.length < 2) return;

    setIsSearching(true);
    try {
      const response = await api.searchConversations(searchQuery, 20);
      setSearchResults(response.conversations);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectConversation = async (conversationId: string) => {
    setArchiveLoading(true);
    try {
      const response = await api.getConversationDetail(conversationId);
      setSelectedConversation(response.conversation);
    } catch (error) {
      console.error('Failed to load conversation detail:', error);
    } finally {
      setArchiveLoading(false);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    if (!confirm('정말 이 대화를 삭제하시겠습니까?')) return;

    try {
      await api.deleteConversation(conversationId);
      // Refresh list
      loadConversations();
      // Clear detail if deleted conversation was selected
      if (selectedConversation?.id === conversationId) {
        setSelectedConversation(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const displayList = searchResults.length > 0 ? searchResults : archiveConversations;

  return (
    <div className="flex h-full w-full">
      {/* Left Panel - Conversation List */}
      <aside className="w-sidebar border-r border-slate-200 bg-slate-50 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-200">
          <button
            onClick={() => setActiveTab('dashboard')}
            className="flex items-center gap-2 text-slate-600 hover:text-primary 
                       transition-colors mb-4 font-semibold"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            대시보드로 돌아가기
          </button>
          
          <h2 className="font-headline font-bold text-slate-900 text-xl mb-4">
            대화 아카이브
          </h2>

          {/* Search */}
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="대화 검색..."
              className="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg
                     focus:outline-none focus:border-primary"
            />
            <button
              onClick={handleSearch}
              disabled={isSearching || searchQuery.length < 2}
              className="px-3 py-2 bg-primary text-white rounded-lg 
                     hover:brightness-110 disabled:opacity-50 transition-all"
            >
              <span className="material-symbols-outlined text-sm">search</span>
            </button>
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2">
          {archiveLoading ? (
            <div className="flex items-center justify-center h-32 text-slate-400">
              <span className="material-symbols-outlined animate-spin">progress_activity</span>
            </div>
          ) : displayList.length === 0 ? (
            <div className="text-center text-slate-400 py-8">
              <span className="material-symbols-outlined text-4xl mb-2">inbox</span>
              <p className="text-sm">저장된 대화가 없습니다</p>
            </div>
          ) : (
            displayList.map((conv) => (
              <div
                key={conv.id}
                onClick={() => handleSelectConversation(conv.id)}
                className={`p-3 rounded-lg cursor-pointer transition-all mb-1
                  ${selectedConversation?.id === conv.id
                    ? 'bg-primary/10 border border-primary/30'
                    : 'hover:bg-slate-100'
                  }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <h3 className="font-semibold text-slate-900 text-sm truncate flex-1">
                    {conv.title}
                  </h3>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteConversation(conv.id);
                    }}
                    className="text-slate-400 hover:text-red-500 transition-colors"
                  >
                    <span className="material-symbols-outlined text-sm">delete</span>
                  </button>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span>{formatDate(conv.started_at)}</span>
                  <span>•</span>
                  <span>{conv.message_count}개 메시지</span>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Right Panel - Conversation Detail */}
      <main className="flex-1 flex flex-col min-w-0 bg-white">
        {selectedConversation ? (
          <>
            {/* Detail Header */}
            <header className="p-6 border-b border-slate-200">
              <h2 className="font-headline font-bold text-slate-900 text-xl">
                {selectedConversation.title}
              </h2>
              <div className="flex items-center gap-4 text-sm text-slate-500 mt-2">
                <span>시작: {formatDate(selectedConversation.started_at)}</span>
                {selectedConversation.ended_at && (
                  <>
                    <span>•</span>
                    <span>종료: {formatDate(selectedConversation.ended_at)}</span>
                  </>
                )}
              </div>
            </header>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {selectedConversation.messages.map((msg, idx) => (
                <MessageBubble
                  key={msg.id || idx}
                  role={msg.sender_type === 'user' ? 'user' : 'manager'}
                  name={msg.sender_type === 'user' ? '나' : '에이전트'}
                  content={msg.content}
                  isUser={msg.sender_type === 'user'}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
            <span className="material-symbols-outlined text-5xl mb-2">chat_bubble_outline</span>
            <p className="text-sm">대화를 선택하세요</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default ArchiveView;
