import React, { useState } from 'react';

interface AddAgentModalProps {
  onClose: () => void;
  onAdd: (data: {
    name: string;
    role: string;
    display_name?: string;
    emoji?: string;
    badge_text?: string;
    icon?: string;
    color?: string;
  }) => void;
}

const ROLES = [
  { id: 'manager', label: '관리자(CEO)', emoji: '👔' },
  { id: 'developer', label: '개발자', emoji: '💻' },
  { id: 'designer', label: '디자이너', emoji: '🎨' },
  { id: 'researcher', label: '연구원', emoji: '📚' },
];

const COLORS = [
  '#4E7EBE', '#4A9B6F', '#7C6BA8', '#D4A055', '#E57373', '#702AE1',
];

const AddAgentModal: React.FC<AddAgentModalProps> = ({ onClose, onAdd }) => {
  const [selectedRole, setSelectedRole] = useState<string>('manager');
  const [displayName, setDisplayName] = useState('');
  const [emoji, setEmoji] = useState('👔');
  const [badgeText, setBadgeText] = useState('');
  const [icon, setIcon] = useState('assignment_ind');
  const [color, setColor] = useState('#4E7EBE');
  
  const handleSubmit = () => {
    const selectedRoleData = ROLES.find(r => r.id === selectedRole);
    onAdd({
      name: selectedRole,
      role: selectedRole,
      display_name: displayName || selectedRoleData?.label,
      emoji,
      badge_text: badgeText,
      icon,
      color,
    });
  };
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
        <h2 className="text-lg font-bold mb-4">새 팀원 추가</h2>
        
        {/* Role Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-600 mb-2">
            역할 선택
          </label>
          <div className="grid grid-cols-2 gap-2">
            {ROLES.map((role) => (
              <button
                key={role.id}
                onClick={() => {
                  setSelectedRole(role.id);
                  setEmoji(role.emoji);
                }}
                className={`p-3 rounded-lg border text-sm ${
                  selectedRole === role.id
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                {role.emoji} {role.label}
              </button>
            ))}
          </div>
        </div>
        
        {/* Display Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-600 mb-1">
            표시 이름
          </label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg"
            placeholder="예: 마케팅팀장"
          />
        </div>
        
        {/* Emoji */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-600 mb-1">
            이모지
          </label>
          <input
            type="text"
            value={emoji}
            onChange={(e) => setEmoji(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-2xl"
          />
        </div>
        
        {/* Badge Text */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-600 mb-1">
            뱃지 텍스트
          </label>
          <input
            type="text"
            value={badgeText}
            onChange={(e) => setBadgeText(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg"
            placeholder="예: 마케팅"
          />
        </div>
        
        {/* Icon */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-600 mb-1">
            아이콘 (Material Symbols)
          </label>
          <input
            type="text"
            value={icon}
            onChange={(e) => setIcon(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg"
            placeholder="예: trending_up"
          />
        </div>
        
        {/* Color */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-600 mb-1">
            색상
          </label>
          <div className="flex gap-2">
            {COLORS.map((c) => (
              <button
                key={c}
                onClick={() => setColor(c)}
                className={`w-8 h-8 rounded-full border-2 ${
                  color === c ? 'border-slate-800' : 'border-transparent'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            취소
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:brightness-110"
          >
            추가
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddAgentModal;
