# Phase 2D: LLM Failover 체계 구현 계획서

> 작업자: Sisyphus (팀 리더)
> 목표: DeepSeek + Gemini 기반 LLM Failover 체계 완성
> 작성일: 2026-04-07

---

## 📋 작업 개요

기존 LLMProviderService를 확장하여 Gemini 2.5 Flash를 폴백 Provider로 추가하고, main.py에 통합합니다.

---

## 🎯 구현 목표

### 1. GeminiProvider 추가
- Gemini 2.5 Flash API 통합
- Google AI Studio API 사용
- DeepSeek 장애 시 자동 전환

### 2. main.py 통합
- Provider 등록 로직 추가
- 환경 변수 기반 설정
- 기본 Provider 우선순위 설정

### 3. 테스트 작성
- LLM Failover 테스트
- Provider 통계 테스트
- Mock Provider 테스트

---

## 🔧 구현 세부사항

### 1. GeminiProvider 구현

```python
class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    @property
    def name(self) -> str:
        return "gemini"
    
    async def call(self, messages: List[Dict], **kwargs) -> LLMResponse:
        # Gemini API 호출 로직
        pass
```

### 2. main.py Provider 등록

```python
from services.llm_provider_service import get_llm_provider_service, DeepSeekProvider, GeminiProvider

def setup_llm_providers():
    service = get_llm_provider_service()
    
    # 1. DeepSeek (Primary)
    if settings.deepseek_api_key:
        service.register_provider(
            "deepseek",
            DeepSeekProvider(
                api_key=settings.deepseek_api_key,
                model="v4"  # 기본 V4, R1 자동 선택
            ),
            is_primary=True
        )
    
    # 2. Gemini (Fallback #1)
    if settings.gemini_api_key:
        service.register_provider(
            "gemini",
            GeminiProvider(
                api_key=settings.gemini_api_key,
                model="gemini-2.5-flash"
            ),
            is_primary=False
        )
    
    # 3. GLM (Fallback #2 - 레거시)
    if settings.glm_api_key:
        service.register_provider(
            "glm",
            GLMProvider(
                api_key=settings.glm_api_key,
                model="glm-4"
            ),
            is_primary=False
        )
```

### 3. LLM Failover 우선순위

```
DeepSeek V4/R1 (Primary) → Gemini 2.5 Flash (Fallback #1) → GLM-4 (Fallback #2)
```

---

## ✅ 구현 체크리스트

### 백엔드
- [ ] `backend/services/llm_provider_service.py` 확장
  - [ ] `GeminiProvider` 클래스 구현
  - [ ] Gemini API 호출 로직
  - [ ] 에러 처리

- [ ] `backend/config.py` 수정
  - [ ] `gemini_api_key` 환경 변수 추가
  - [ ] `gemini_model` 설정 추가

- [ ] `backend/main.py` 수정
  - [ ] `setup_llm_providers()` 함수 추가
  - [ ] startup 이벤트에 등록

### 테스트
- [ ] `backend/tests/test_llm_provider.py` 생성
  - [ ] Provider 등록 테스트
  - [ ] Failover 테스트
  - [ ] 통계 추적 테스트
  - [ ] Mock Provider 테스트

### 문서화
- [ ] `.env.example` 업데이트
  - [ ] `GEMINI_API_KEY` 추가
  - [ ] 주석 추가

---

## 🔗 의존성

- **선행 작업**: Phase 2C (메모리 관리) ✅ 완료
- **후행 작업**: Phase 3 (초대 및 협업)

---

## ⚠️ 주의사항

1. **Gemini API Key**: Google AI Studio에서 발급 필요
2. **Rate Limiting**: Gemini API 호출 제한 확인
3. **타임아웃**: Gemini API 타임아웃 설정 (기본 60초)
4. **에러 처리**: 429 Too Many Requests 대응

---

## 📊 예상 소요 시간

- 구현: 1-2시간
- 테스트: 1시간
- 총: 2-3시간

---

**작업 담당자: @Sisyphus 👑**
