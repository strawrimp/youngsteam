import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { InviteSuggestion } from '../types';

interface InviteModalProps {
  isOpen: boolean;
  suggestion: InviteSuggestion | null;
  onAccept: () => void;
  onReject: () => void;
  onClose: () => void;
}

export const InviteModal: React.FC<InviteModalProps> = ({
  isOpen,
  suggestion,
  onAccept,
  onReject,
  onClose,
}) => {
  if (!suggestion) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md"
          >
            <div className="glass-card p-6 mx-4">
              {/* Header */}
              <div className="flex items-center gap-3 mb-4">
                <div className="text-3xl">{suggestion.agent_name?.charAt(0) === '김' ? '👔' : 
                                          suggestion.agent_name?.charAt(0) === '박' ? '💻' :
                                          suggestion.agent_name?.charAt(0) === '이' ? '🎨' : '🔍'}</div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    에이전트 초대 제안
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    선임에이전트의 추천
                  </p>
                </div>
              </div>

              {/* Agent Info */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="text-2xl">
                    {suggestion.agent_name?.charAt(0) === '김' ? '👔' : 
                     suggestion.agent_name?.charAt(0) === '박' ? '💻' :
                     suggestion.agent_name?.charAt(0) === '이' ? '🎨' : '🔍'}
                  </div>
                  <div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {suggestion.agent_name}
                    </div>
                    <div className="text-sm text-slate-600 dark:text-slate-400">
                      {suggestion.agent_role}
                    </div>
                  </div>
                </div>
                <div className="mt-3 p-3 bg-white/50 dark:bg-white/10 rounded-lg">
                  <div className="text-sm text-slate-700 dark:text-slate-300">
                    <span className="font-medium">추천 사유:</span>
                    <p className="mt-1">{suggestion.reason}</p>
                  </div>
                  <div className="mt-2 flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                      신뢰도: {Math.round(suggestion.confidence * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={onReject}
                  className="flex-1 px-4 py-2.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                >
                  나중에
                </button>
                <button
                  onClick={onAccept}
                  className="flex-1 px-4 py-2.5 rounded-lg bg-blue-500 text-white font-medium hover:bg-blue-600 transition-colors shadow-lg shadow-blue-500/30"
                >
                  초대하기
                </button>
              </div>

              {/* Close button */}
              <button
                onClick={onClose}
                className="absolute top-4 right-4 p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <svg
                  className="w-5 h-5 text-slate-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
