# Phase 2C: 메모리 관리 시스템 구현 계획서

> 작업자: Sisyphus (팀 리더)
> 목표: 개별 에이전트 메모리 시스템 구축
> 작성일: 2026-04-07

---

## 📋 작업 개요

기존 `MemoryService`를 확장하여 개별 에이전트 메모리, 파일 기반 저장, 메모리 병합 로직을 구현합니다.

---

## 🎯 구현 목표

### 1. 개별 에이전트 메모리
- 각 에이전트별 독립된 memory.json 파일 관리
- 경로: `backend/agents/workspaces/{agent_name}/memory.json`
- 대화 기록, 컨텍스트, 작업 상태 저장

### 2. 파일 기반 저장
- JSON 형식으로 메모리 영속화
- 자동 디렉토리 생성
- 파일 존재하지 않을 시 기본 템플릿 생성

### 3. 메모리 병합
- 프로젝트 공유 메모리 + 개별 에이전트 메모리 통합
- LLM 프롬프트에 주입할 컨텍스트 생성

### 4. 메모리 정리
- 오래된 대화 자동 삭제 (기본 30일 보관)
- 컨텍스트 윈도우 관리 (최대 토큰 수 제한)

### 5. 동시성 제어
- 파일 읽기/쓰기 충돌 방지
- `asyncio.Lock` 사용

---

## 🗂️ 메모리 JSON 스키마

### 개별 에이전트 메모리 (`workspaces/{agent}/memory.json`)

```json
{
  "agent_name": "developer",
  "project_id": 1,
  "conversations": [
    {
      "id": "conv_001",
      "timestamp": "2026-04-07T10:00:00Z",
      "role": "user",
      "content": "API 설계 부탁드립니다",
      "metadata": {}
    },
    {
      "id": "conv_002",
      "timestamp": "2026-04-07T10:00:05Z",
      "role": "agent",
      "content": "네, REST API로 설계하겠습니다",
      "metadata": {
        "model": "deepseek-chat",
        "tokens": 150
      }
    }
  ],
  "context": {
    "current_task": "API 설계",
    "last_updated": "2026-04-07T10:00:05Z",
    "project_context": "이커머스 웹사이트 개발"
  },
  "settings": {
    "max_conversations": 100,
    "retention_days": 30
  }
}
```

### 프로젝트 공유 메모리 (DB)

기존 `shared_memory` 테이블 활용 (이미 구현됨)

---

## 🔧 구현 세부사항

### 1. `backend/services/memory_service.py` 확장

#### 추가할 메서드

```python
class MemoryService:
    # 기존 메서드 유지...
    
    # 새로 추가할 메서드들
    async def load_agent_memory(self, agent_name: str, project_id: int) -> Dict:
        """개별 에이전트 메모리 로드"""
        pass
    
    async def save_agent_memory(self, agent_name: str, project_id: int, memory: Dict):
        """개별 에이전트 메모리 저장"""
        pass
    
    async def add_conversation(self, agent_name: str, project_id: int, role: str, content: str, metadata: Dict = None):
        """대화 기록 추가"""
        pass
    
    async def get_merged_context(self, agent_name: str, project_id: int) -> str:
        """개별 메모리 + 공유 메모리 병합 컨텍스트 반환"""
        pass
    
    async def cleanup_old_conversations(self, agent_name: str, project_id: int, days: int = 30):
        """오래된 대화 정리"""
        pass
    
    def _get_memory_path(self, agent_name: str) -> str:
        """메모리 파일 경로 반환"""
        pass
    
    def _ensure_workspace_exists(self, agent_name: str):
        """워크스페이스 디렉토리 생성"""
        pass
    
    def _create_default_memory(self, agent_name: str, project_id: int) -> Dict:
        """기본 메모리 템플릿 생성"""
        pass
```

### 2. 동시성 제어

```python
import asyncio
from pathlib import Path

class MemoryService:
    def __init__(self, db_session=None):
        self.db = db_session
        self.in_memory_cache: Dict[str, List[Dict]] = {}
        self._file_locks: Dict[str, asyncio.Lock] = {}
    
    async def _get_file_lock(self, agent_name: str) -> asyncio.Lock:
        """에이전트별 파일 잠금 반환"""
        if agent_name not in self._file_locks:
            self._file_locks[agent_name] = asyncio.Lock()
        return self._file_locks[agent_name]
```

### 3. 워크스페이스 구조

```
backend/
└── agents/
    └── workspaces/
        ├── manager/
        │   ├── SOUL.md
        │   ├── AGENTS.md
        │   └── memory.json
        ├── developer/
        │   ├── SOUL.md
        │   ├── AGENTS.md
        │   └── memory.json
        ├── designer/
        │   └── memory.json
        └── researcher/
            └── memory.json
```

---

## ✅ 구현 체크리스트

### 백엔드
- [ ] `backend/services/memory_service.py` 확장
  - [ ] `load_agent_memory()` 구현
  - [ ] `save_agent_memory()` 구현
  - [ ] `add_conversation()` 구현
  - [ ] `get_merged_context()` 구현
  - [ ] `cleanup_old_conversations()` 구현
  - [ ] `_get_memory_path()` 구현
  - [ ] `_ensure_workspace_exists()` 구현
  - [ ] `_create_default_memory()` 구현
  - [ ] 파일 잠금 메커니즘 추가

### 테스트
- [ ] `backend/tests/test_memory_service.py` 생성
  - [ ] 메모리 로드/저장 테스트
  - [ ] 대화 추가 테스트
  - [ ] 컨텍스트 병합 테스트
  - [ ] 정리 로직 테스트
  - [ ] 동시성 테스트

### 문서화
- [ ] `backend/services/memory_service.py` docstring 업데이트
- [ ] 메모리 JSON 스키마 문서화

---

## 🔗 의존성

- **선행 작업**: Phase 2A (SOUL.md 로더), Phase 2B (에이전트 바인딩) ✅ 완료
- **후행 작업**: Phase 2D (DeepSeek + Gemini API 통합)

---

## ⚠️ 주의사항

1. **파일 경로**: `backend/agents/workspaces/` 디렉토리가 존재하는지 확인
2. **동시성**: 여러 에이전트가 동시에 메모리 접근 시 잠금 사용
3. **에러 처리**: 파일 없음, JSON 파싱 오류, 권한 오류 처리
4. **성능**: 메모리 파일이 커질 경우 로딩 최적화 필요

---

## 📊 예상 소요 시간

- 구현: 2-3시간
- 테스트: 1시간
- 총: 3-4시간

---

**작업 담당자: @Sisyphus 👑**
