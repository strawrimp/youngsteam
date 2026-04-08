# AGENTS.md

이 파일은 OpenCode AI 에이전트가 프로젝트를 이해하는 데 필요한 정보를 제공합니다.

## Project Overview

<!-- 프로젝트 설명을 여기에 작성하세요 -->

## Current Progress

### Completed
- ✅ 프로젝트 초기화

### In Progress
- 🔄 개발 중

### Pending
- ⏳ 대기 중

## Build Commands

### Core Commands
- `npm install` - 의존성 설치
- `npm run dev` - 개발 서버 실행
- `npm run build` - 프로덕션 빌드

## Code Style Guidelines

### TypeScript
- Target: ES2022
- Strict mode enabled
- Functional components with React.FC

### Naming Conventions
- **Components**: PascalCase
- **Functions/Variables**: camelCase
- **Constants**: UPPER_SNAKE_CASE
- **Types/Interfaces**: PascalCase

### Styling (Tailwind CSS)
- Use utility classes
- Spacing: `p-3`, `m-2`, `gap-4`
- Colors: `text-gray-800`, `bg-emerald-500`

## Multi-Agent System (Oh My OpenCode)

### Agent Roles

| 에이전트 | 역할 | 전문분야 |
|---------|------|---------|
| **Sisyphus** | 팀 리더 | 설계, 조율, 의사결정 |
| **Oracle** | 코드 아키텍트 | 코드작성, 리팩토링, 최적화 |
| **Frontend-Engineer** | 프론트엔드 전문가 | React, TypeScript, UI/UX |
| **Librarian** | 문서 검색 | 문서검색, 정보요약 |
| **Explore** | 코드 네비게이터 | 파일탐색, 코드분석 |
| **Multimodal-Looker** | 비전 분석 | 이미지분석, 디자인변환 |

### Workflow Patterns

1. **코드 생성**: Sisyphus → Oracle
2. **프론트엔드**: Sisyphus → Frontend-Engineer
3. **문서 작업**: Sisyphus → Librarian
4. **코드 탐색**: Sisyphus → Explore
5. **디자인 변환**: Sisyphus → Multimodal-Looker

## Auto-Applied Skills

이 프로젝트에서 자동으로 적용되는 스킬:
- `vercel-react-best-practices` - React 성능 최적화
- `web-design-guidelines` - 웹 디자인 가이드라인
- `frontend-design` - 프론트엔드 디자인 패턴
