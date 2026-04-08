import React from 'react';

interface EmojiPickerProps {
  onSelect: (emoji: string) => void;
  onClose: () => void;
}

const EMOJIS = [
  '👔', '💼', '🎨', '📚', '📢', '🏆', '🎯', '🔬', '📝', '📈',
  '📋', '📊', '💰', '🧐', '🌟', '🎁', '📌', '👀', '⚙️', '📑',
  '🔢', '📐', '🌐', '🦠', '🗓', '🔎', '💎', '🔴', '💻', '🎨',
];

const EmojiPicker: React.FC<EmojiPickerProps> = ({ onSelect, onClose }) => {
  return (
    <div className="absolute top-full left-0 mt-1 p-2 bg-white border border-slate-200 
                    rounded-lg shadow-lg z-50 grid grid-cols-6 gap-1">
      {EMOJIS.map((emoji, index) => (
        <button
          key={index}
          onClick={() => onSelect(emoji)}
          className="w-8 h-8 flex items-center justify-center hover:bg-slate-100 rounded"
        >
          {emoji}
        </button>
      ))}
    </div>
  );
};

export default EmojiPicker;
