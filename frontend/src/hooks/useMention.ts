import { useState, useCallback } from 'react';
import { MentionCandidate } from '../types';

interface MentionState {
  isActive: boolean;
  candidates: MentionCandidate[];
  selectedIndex: number;
  query: string;
}

interface UseMentionProps {
  agents: any[];
  onMention?: (agentId: string) => void;
}

interface UseMentionReturn {
  mentionState: MentionState;
  handleInput: (value: string, cursorPosition: number) => void;
  selectCandidate: (
    candidate: MentionCandidate,
    inputValue: string,
    cursorPosition: number
  ) => { newValue: string; newCursorPosition: number } | null;
  handleKeyDown: (e: React.KeyboardEvent) => boolean | { shouldSelect: boolean; candidate: MentionCandidate };
}

export const useMention = ({ agents, onMention }: UseMentionProps): UseMentionReturn => {
  const [mentionState, setMentionState] = useState<MentionState>({
    isActive: false,
    candidates: [],
    selectedIndex: 0,
    query: '',
  });

  // Convert agents to MentionCandidates
  const getCandidates = useCallback(
    (query: string): MentionCandidate[] => {
      if (!agents || agents.length === 0) return [];
      
      const candidates = agents.map((agent) => ({
        id: agent.id || agent.name,
        name: agent.name,
        role: agent.role || agent.id,
        display_name: agent.display_name || agent.name,
        emoji: agent.emoji || '🤖',
      }));

      if (!query) return candidates;

      return candidates.filter(
        (agent) =>
          agent.name.toLowerCase().includes(query.toLowerCase()) ||
          agent.role.toLowerCase().includes(query.toLowerCase()) ||
          (agent.display_name && agent.display_name.toLowerCase().includes(query.toLowerCase()))
      );
    },
    [agents]
  );

  // Handle input changes to detect @ mentions
  const handleInput = useCallback(
    (value: string, cursorPosition: number) => {
      // Find @ symbol before cursor
      const textBeforeCursor = value.substring(0, cursorPosition);
      const lastAtIndex = textBeforeCursor.lastIndexOf('@');

      if (lastAtIndex === -1) {
        // No @ symbol, close mention list
        setMentionState({
          isActive: false,
          candidates: [],
          selectedIndex: 0,
          query: '',
        });
        return;
      }

      // Check if there's a space between @ and cursor (which would cancel the mention)
      const textAfterAt = textBeforeCursor.substring(lastAtIndex + 1);
      if (textAfterAt.includes(' ')) {
        setMentionState({
          isActive: false,
          candidates: [],
          selectedIndex: 0,
          query: '',
        });
        return;
      }

      // Extract query after @
      const query = textAfterAt;
      const candidates = getCandidates(query);

      setMentionState({
        isActive: true,
        candidates,
        selectedIndex: 0,
        query,
      });
    },
    [getCandidates]
  );

  // Select a candidate and insert it into the text
  const selectCandidate = useCallback(
    (
      candidate: MentionCandidate,
      inputValue: string,
      cursorPosition: number
    ): { newValue: string; newCursorPosition: number } | null => {
      // Find @ symbol before cursor
      const textBeforeCursor = inputValue.substring(0, cursorPosition);
      const lastAtIndex = textBeforeCursor.lastIndexOf('@');

      if (lastAtIndex === -1) return null;

      // Replace from @ to cursor with @name
      const textBefore = inputValue.substring(0, lastAtIndex);
      const textAfter = inputValue.substring(cursorPosition);
      const mentionText = `@${candidate.name} `;
      const newValue = textBefore + mentionText + textAfter;
      const newCursorPosition = lastAtIndex + mentionText.length;

      // Call onMention callback
      if (onMention) {
        onMention(candidate.id);
      }

      // Close mention list
      setMentionState({
        isActive: false,
        candidates: [],
        selectedIndex: 0,
        query: '',
      });

      return { newValue, newCursorPosition };
    },
    [onMention]
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent): boolean | { shouldSelect: boolean; candidate: MentionCandidate } => {
      if (!mentionState.isActive || mentionState.candidates.length === 0) {
        return false;
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setMentionState((prev) => ({
            ...prev,
            selectedIndex: Math.min(prev.selectedIndex + 1, prev.candidates.length - 1),
          }));
          return true;

        case 'ArrowUp':
          e.preventDefault();
          setMentionState((prev) => ({
            ...prev,
            selectedIndex: Math.max(prev.selectedIndex - 1, 0),
          }));
          return true;

        case 'Tab':
        case 'Enter':
          if (mentionState.candidates[mentionState.selectedIndex]) {
            e.preventDefault();
            return {
              shouldSelect: true,
              candidate: mentionState.candidates[mentionState.selectedIndex],
            };
          }
          return false;

        case 'Escape':
          e.preventDefault();
          setMentionState({
            isActive: false,
            candidates: [],
            selectedIndex: 0,
            query: '',
          });
          return true;

        default:
          return false;
      }
    },
    [mentionState.isActive, mentionState.candidates, mentionState.selectedIndex]
  );

  return {
    mentionState,
    handleInput,
    selectCandidate,
    handleKeyDown,
  };
};
