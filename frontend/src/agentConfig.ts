import { Agent } from './types';

// 기본값 폴백 (DB에 값이 없을 때 사용)
const DEFAULTS: Record<string, AgentDisplay> = {
  manager: {
    display_name: '네오 비서실장',
    emoji: '👔',
    badge_text: '비서실장',
    icon: 'assignment_ind',
    color: '#4E7EBE',
    description: '전체 프로젝트를 총괄하고 팀원 간 조율을 담당합니다. 일정 관리, 우선순위 결정, 최종 의사결정을 지원합니다.',
  },
  developer: {
    display_name: '아서 개발부장',
    emoji: '💻',
    badge_text: '개발부장',
    icon: 'terminal',
    color: '#4A9B6F',
    description: '시스템 아키텍처 설계와 핵심 코드 구현을 담당합니다. 기술 스택 선정, 성능 최적화, 코드 리뷰를 수행합니다.',
  },
  designer: {
    display_name: '소피아 디자이너',
    emoji: '🎨',
    badge_text: '디자이너',
    icon: 'palette',
    color: '#7C6BA8',
    description: '사용자 경험 설계와 비주얼 디자인을 담당합니다. UI/UX 프로토타이핑, 디자인 시스템 구축, 브랜드 아이덴티티를 관리합니다.',
  },
  researcher: {
    display_name: '루나 연구소장',
    emoji: '📚',
    badge_text: '연구소장',
    icon: 'biotech',
    color: '#D4A055',
    description: '최신 기술 동향 분석과 데이터 기반 인사이트를 제공합니다. 시장 조사, 경쟁사 분석, 기술 검증을 수행합니다.',
  },
  bot: {
    display_name: '클로',
    emoji: '🤖',
    badge_text: '봇',
    icon: 'smart_toy',
    color: '#E85D3A',
    description: 'Mac Mini 게이트웨이를 통해 실제 기기를 제어하고 명령을 실행합니다. WebSocket으로 연결되어 있습니다.',
  },
};

export interface AgentDisplay {
  display_name: string;
  emoji: string;
  badge_text: string;
  icon: string;
  color: string;
  description?: string;
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
        description: DEFAULTS[agent.role]?.description || '',
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
    description: '',
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
    case 'bot':
      return 'bg-white text-orange-600 shadow-sm border border-slate-100';
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
    case 'bot':
      return 'text-orange-600';
    default:
      return 'text-primary';
  }
}

/**
 * 역할에 따른 Tailwind bg/border/text 클래스 반환 (다크모드 지원)
 * Sidebar 활성 상태, VotingPanel 카드 등에서 공통 사용
 */
export function getRoleTailwindClass(role: string, isDark: boolean = false): string {
  switch (role) {
    case 'manager':
      return isDark
        ? 'bg-slate-900/40 border-slate-800 text-slate-300'
        : 'bg-slate-50 border-slate-100 text-slate-700';
    case 'developer':
      return isDark
        ? 'bg-emerald-900/30 border-emerald-800 text-emerald-300'
        : 'bg-emerald-50 border-emerald-100 text-emerald-700';
    case 'designer':
      return isDark
        ? 'bg-purple-900/30 border-purple-800 text-purple-300'
        : 'bg-purple-50 border-purple-100 text-purple-700';
    case 'researcher':
      return isDark
        ? 'bg-amber-900/30 border-amber-800 text-amber-300'
        : 'bg-amber-50 border-amber-100 text-amber-700';
    case 'bot':
      return isDark
        ? 'bg-orange-900/30 border-orange-800 text-orange-300'
        : 'bg-orange-50 border-orange-100 text-orange-700';
    default:
      return isDark
        ? 'bg-slate-800 border-slate-700 text-slate-300'
        : 'bg-slate-50 border-slate-100 text-slate-700';
  }
}

/**
 * ★ 폴백 에이전트 배열 생성
 * 백엔드 API(/api/agents)가 실패할 때 사용합니다.
 * DB가 비어있거나 서버가 꺼져있어도 사이드바에 에이전트가 표시됩니다.
 */
export function getFallbackAgents(): Agent[] {
  const roles = (Object.keys(DEFAULTS) as (keyof typeof DEFAULTS)[]).filter(r => r !== 'bot');
  return roles.map((role) => {
    const d = DEFAULTS[role];
    return {
      id: role,  // role 자체를 ID로 사용 (폴백용)
      name: d.display_name.split(' ')[0],  // "네오", "아서" 등
      role: role as Agent['role'],
      display_name: d.display_name,
      emoji: d.emoji,
      badge_text: d.badge_text,
      icon: d.icon,
      color: d.color,
      status: 'active',
    };
  });
}
