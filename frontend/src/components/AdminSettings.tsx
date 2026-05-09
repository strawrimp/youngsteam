import React, { useState, useEffect } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';
import { Agent, TeamSettings } from '../types';
import AddAgentModal from './AddAgentModal';
import EmojiPicker from './EmojiPicker';

const AdminSettings: React.FC = () => {
  const { agents, setAgents, teamSettings, setTeamSettings } = useConversationStore();
  
  const [isLoading, setIsLoading] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, Partial<Agent>>>({});
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState<string | null>(null);
  
  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    setIsLoading(true);
    try {
      const [agentsData, settingsData] = await Promise.all([
        api.getAgents(),
        api.getTeamSettings(),
      ]);
      setAgents(agentsData.agents);
      setTeamSettings(settingsData);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleTeamSettingsUpdate = async (field: keyof TeamSettings, value: string) => {
    if (!teamSettings) return;
    
    const newSettings = { ...teamSettings, [field]: value };
    setTeamSettings(newSettings);
    
    try {
      await api.updateTeamSettings({ [field]: value });
    } catch (error) {
      console.error('Failed to update team settings:', error);
    }
  };
  
  const handleAgentFieldChange = (agentId: string, field: keyof Agent, value: string) => {
    setEditForm(prev => ({
      ...prev,
      [agentId]: {
        ...prev[agentId],
        [field]: value,
      },
    }));
  };
  
  const handleAgentSave = async (agentId: string) => {
    const changes = editForm[agentId];
    if (!changes) return;
    
    try {
      await api.updateAgent(agentId, changes);
      
      // Update local state
      setAgents(agents.map(a => 
        a.id === agentId ? { ...a, ...changes } : a
      ));
      
      setEditForm(prev => {
        const newState = { ...prev };
        delete newState[agentId];
        return newState;
      });
    } catch (error) {
      console.error('Failed to update agent:', error);
    }
  };
  
  const handleDeleteAgent = async (agentId: string) => {
    if (agents.length <= 2) {
      alert('최소 2명의 에이전트가 필요합니다.');
      return;
    }
    
    if (!confirm('정말 이 에이전트를 삭제하시겠습니까?')) return;
    
    try {
      await api.deleteAgent(agentId);
      setAgents(agents.filter(a => a.id !== agentId));
    } catch (error) {
      console.error('Failed to delete agent:', error);
    }
  };
  
  const handleAddAgent = async (data: {
    name: string;
    role: string;
    display_name?: string;
    emoji?: string;
    badge_text?: string;
    icon?: string;
    color?: string;
  }) => {
    try {
      const response = await api.createAgent(data);
      setAgents([...agents, response]);
      setShowAddModal(false);
    } catch (error) {
      console.error('Failed to create agent:', error);
    }
  };
  
  const getRoleLabel = (role: string): string => {
    const labels: Record<string, string> = {
      manager: '네오 비서실장',
      developer: '아서 개발부장',
      designer: '소피아 디자이너',
      researcher: '루나 연구소장',
    };
    return labels[role] || role;
  };
  
  const getColorOptions = (): string[] => [
    '#4E7EBE', '#4A9B6F', '#7C6BA8', '#D4A055', '#E57373', '#702AE1',
  ];
  
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-slate-500">로딩 중...</div>
      </div>
    );
  }
  
  return (
    <div className="flex-1 overflow-y-auto p-8 bg-slate-50">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-headline font-bold text-slate-800">
          ⚙️ 관리자 설정
        </h1>
        <button
          onClick={() => useConversationStore.getState().setActiveTab('dashboard')}
          className="text-primary hover:underline"
        >
          ← 대시보드로 돌아가기
        </button>
      </div>
      
      {/* Team Settings Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h2 className="text-lg font-headline font-bold text-slate-700 mb-1">
          팀 설정
        </h2>
        <p className="text-sm text-slate-400 mb-4">
          팀의 이름과 아이콘을 설정하여 대시보드를 개인화하세요
        </p>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              팀 이름
            </label>
            <input
              type="text"
              value={teamSettings?.team_name || ''}
              onChange={(e) => handleTeamSettingsUpdate('team_name', e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              팀 부제목
            </label>
            <input
              type="text"
              value={teamSettings?.team_subtitle || ''}
              onChange={(e) => handleTeamSettingsUpdate('team_subtitle', e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              팀 아이콘
            </label>
            <input
              type="text"
              value={teamSettings?.team_icon || ''}
              onChange={(e) => handleTeamSettingsUpdate('team_icon', e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
              placeholder="Material Symbols 아이콘 이름"
            />
          </div>
        </div>
      </div>
      
      {/* Agents Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-headline font-bold text-slate-700">
            에이전트 관리
          </h2>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:brightness-110 transition-all"
          >
            + 새 팀원 추가
          </button>
        </div>
        <p className="text-sm text-slate-400 mb-4">
          AI 팀원들의 역할, 아이콘, 색상을 관리합니다. 변경사항은 즉시 적용됩니다.
        </p>
        
        <div className="space-y-4">
          {agents.map((agent) => (
            <div key={agent.id} className="border border-slate-200 rounded-lg p-4">
              <div className="flex items-start gap-4">
                {/* Emoji */}
                <div className="relative">
                  <button
                    onClick={() => setShowEmojiPicker(agent.id)}
                    className="text-2xl hover:bg-slate-100 rounded p-1"
                  >
                    {editForm[agent.id]?.emoji || agent.emoji || '👤'}
                  </button>
                  {showEmojiPicker === agent.id && (
                    <EmojiPicker
                      onSelect={(emoji) => {
                        handleAgentFieldChange(agent.id, 'emoji', emoji);
                        setShowEmojiPicker(null);
                      }}
                      onClose={() => setShowEmojiPicker(null)}
                    />
                  )}
                </div>
                
                {/* Agent Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <input
                      type="text"
                      value={editForm[agent.id]?.display_name || agent.display_name || ''}
                      onChange={(e) => handleAgentFieldChange(agent.id, 'display_name', e.target.value)}
                      className="font-bold text-slate-800 bg-transparent border-none focus:ring-0 p-0"
                      placeholder="표시 이름"
                    />
                    <span className="text-xs text-slate-400">({getRoleLabel(agent.role)})</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <label className="block text-xs text-slate-500 mb-1">뱃지 텍스트</label>
                      <input
                        type="text"
                        value={editForm[agent.id]?.badge_text || agent.badge_text || ''}
                        onChange={(e) => handleAgentFieldChange(agent.id, 'badge_text', e.target.value)}
                        className="w-full px-2 py-1 border border-slate-200 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-500 mb-1">아이콘</label>
                      <input
                        type="text"
                        value={editForm[agent.id]?.icon || agent.icon || ''}
                        onChange={(e) => handleAgentFieldChange(agent.id, 'icon', e.target.value)}
                        className="w-full px-2 py-1 border border-slate-200 rounded text-sm"
                        placeholder="Material Symbols"
                      />
                    </div>
                  </div>
                  
                  {/* Color Picker */}
                  <div className="mt-2">
                    <label className="block text-xs text-slate-500 mb-1">색상</label>
                    <div className="flex gap-1">
                      {getColorOptions().map((color) => (
                        <button
                          key={color}
                          onClick={() => handleAgentFieldChange(agent.id, 'color', color)}
                          className={`w-6 h-6 rounded-full border-2 ${
                            (editForm[agent.id]?.color || agent.color) === color
                              ? 'border-slate-800'
                              : 'border-transparent'
                          }`}
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
                
                {/* Actions */}
                <div className="flex flex-col gap-2">
                  {editForm[agent.id] && (
                    <button
                      onClick={() => handleAgentSave(agent.id)}
                      className="px-3 py-1 bg-emerald-500 text-white rounded text-sm hover:bg-emerald-600"
                    >
                      저장
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteAgent(agent.id)}
                    className="px-3 py-1 text-red-500 hover:bg-red-50 rounded text-sm"
                  >
                    삭제
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* System Info */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-lg font-headline font-bold text-slate-700 mb-1">
          시스템 정보
        </h2>
        <p className="text-sm text-slate-400 mb-4">
          현재 시스템의 실행 환경과 리소스 사용 현황입니다
        </p>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-50 rounded-lg p-4 text-center">
            <span className="material-symbols-outlined text-2xl text-primary mb-1">group</span>
            <p className="text-2xl font-bold text-slate-800">{agents.length}</p>
            <p className="text-xs text-slate-500">활성 에이전트</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 text-center">
            <span className="material-symbols-outlined text-2xl text-emerald-600 mb-1">psychology</span>
            <p className="text-sm font-bold text-slate-800">DeepSeek</p>
            <p className="text-xs text-slate-500">LLM 엔진</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 text-center">
            <span className="material-symbols-outlined text-2xl text-purple-600 mb-1">database</span>
            <p className="text-sm font-bold text-slate-800">SQLite</p>
            <p className="text-xs text-slate-500">데이터베이스</p>
          </div>
        </div>
      </div>
      
      {/* Add Agent Modal */}
      {showAddModal && (
        <AddAgentModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddAgent}
        />
      )}
    </div>
  );
};

export default AdminSettings;
