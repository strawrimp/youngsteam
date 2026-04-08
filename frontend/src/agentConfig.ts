import { Agent } from './types';

// 기본값 폴백 (DB에 값이 없을 때 사용)
const DEFAULTS: Record<string, AgentDisplay> = {
  manager: {
    display_name: '비서실장',
    emoji: '👔',
    badge_text: '책임',
    icon: 'assignment_ind',
    color: '#4E7EBE',
  },
  developer: {
    display_name: '개발부장',
    emoji: '💻',
    badge_text: '기술',
    icon: 'terminal',
    color: '#4A9B6F',
  },
  designer: {
    display_name: '디자이너',
    emoji: '🎨',
    badge_text: '디자인',
    icon: 'palette',
    color: '#7C6BA8',
  },
  researcher: {
    display_name: '연구소장',
    emoji: '📚',
    badge_text: '연구',
    icon: 'biotech',
    color: '#D4A055',
  },
};

export interface AgentDisplay {
  display_name: string;
  emoji: string;
  badge_text: string;
  icon: string;
  color: string;
}

/**
 * 에이전트 설정을 가져옵니다.
 * store의 agents 배열에서 id 또는 role로 찾고, 없으면 기본값을 반환합니다.
 */
export function getAgentConfig(
  agentIdOrRole: string,
  agents?: Agent[]
): AgentDisplay {
  // agents 배열이 제공된 경우 먼저 검색
  if (agents && agents.length > 0) {
    // ID로 먼저 검색
    let agent = agents.find(a => a.id === agentIdOrRole);
    
    // ID로 못 찾으면 role로 검색
    if (!agent) {
      agent = agents.find(a => a.role === agentIdOrRole);
    }
    
    // name 또는 display_name으로 검색
    if (!agent) {
      agent = agents.find(a => 
        a.name === agentIdOrRole || a.display_name === agentIdOrRole
      );
    }
    
    if (agent) {
      // Lucide/PascalCase icon names (UserCog, Code, Palette, Search) are not Material Symbols.
      // Material Symbols uses all-lowercase ligature names. Any name starting with
      // an uppercase letter is treated as a non-Material-Symbol name.
      const isLucideIcon = (str: string) => /^[A-Z]/.test(str);
      
      const displayName = agent.display_name 
        && !isLucideIcon(agent.display_name)
        ? agent.display_name 
        : DEFAULTS[agent.role]?.display_name || agent.name;
      
      const icon = agent.icon 
        && !isLucideIcon(agent.icon) 
        ? agent.icon 
        : DEFAULTS[agent.role]?.icon || 'person';
      
      return {
        display_name: displayName,
        emoji: agent.emoji || DEFAULTS[agent.role]?.emoji || '👤',
        badge_text: agent.badge_text || DEFAULTS[agent.role]?.badge_text || '',
        icon,
        color: agent.color || DEFAULTS[agent.role]?.color || '#6B7280',
      };
    }
  }
  
  // 기본값 반환
  return DEFAULTS[agentIdOrRole] || {
    display_name: agentIdOrRole,
    emoji: '👤',
    badge_text: '',
    icon: 'person',
    color: '#6B7280',
  };
}

/**
 * 역할에 따른 Tailwind 색상 클래스 반환 (CDN Tailwind용)
 */
export function getRoleColorClass(role: string, isActive: boolean = true): string {
  if (!isActive) return 'text-slate-500 hover:bg-slate-200/50';
  
  switch (role) {
    case 'manager':
      return 'bg-white text-primary shadow-sm border border-slate-100';
    case 'developer':
      return 'bg-white text-emerald-600 shadow-sm border border-slate-100';
    case 'designer':
      return 'bg-white text-purple-600 shadow-sm border border-slate-100';
    case 'researcher':
      return 'bg-white text-amber-600 shadow-sm border border-slate-100';
    default:
      return 'bg-white text-primary shadow-sm border border-slate-100';
  }
}

/**
 * 역할에 따른 아이콘 색상 클래스 반환
 */
export function getIconColorClass(role: string, isActive: boolean = true): string {
  if (!isActive) return 'text-slate-500';
  
  switch (role) {
    case 'manager':
      return 'text-primary';
    case 'developer':
      return 'text-emerald-600';
    case 'designer':
      return 'text-purple-600';
    case 'researcher':
      return 'text-amber-600';
    default:
      return 'text-primary';
  }
}
