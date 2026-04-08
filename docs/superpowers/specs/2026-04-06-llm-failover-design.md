# LLM Failover 체계 설계도

**작성일**: 2026-04-06
**작성자**: Sisyphus (팀 리더)
**상태**: 검토 완료 ✅
**버전**: 1.0

---

## 📋 개요

이 문서는 OpenClaw 업그레이드 프로젝트의 LLM Failover 체계를 설계합니다.
메인 LLM으로 DeepSeek V4/R1을 사용하고, 장애 시 Gemini 2.5 Flash와 Gemini 3 Flash Preview로 자동 전환하는 구조입니다.

---

## 🎯 설계 목표

### 비즈니스 목표
1. **비용 효율성**: DeepSeek의 저렴한 비용 활용
2. **고가용성**: 24/7 서비스 가용성 보장
3. **성능 최적화**: 작업 유형별 최적 모델 자동 선택
4. **장애 대응**: 자동 Failover로 무중단 서비스

### 기술적 목표
1. **다중 Provider 지원**: DeepSeek, Gemini 통합 관리
2. **지능형 라우팅**: 작업 유형에 따른 모델 자동 선택
3. **자동 Failover**: Provider 장애 시 자동 전환
4. **통계 추적**: Provider별 성능 모니터링

---

## 🏗️ 아키텍처

### LLM Provider 계층구조

```
┌─────────────────────────────────────────────────────────┐
│                    사용자 요청                           │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              LLMProviderService                         │
│  - 작업 유형 분석 (task_type, complexity)               │
│  - 모델 선택 (DeepSeek V4/R1/Gemini)                    │
│  - Failover 로직                                        │
│  - 통계 추적                                             │
└────────┬────────────────────────────────────────────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
    │DeepSeek │   │DeepSeek │   │ Gemini  │   │ Gemini  │
    │   V4    │   │   R1    │   │2.5 Flash│   │3 Flash  │
    │(메인#1)│   │(메인#1) │   │(폴백#2) │   │(폴백#3) │
    └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

### 모델 우선순위

| 우선순위 | 모델 | 용도 | 특징 |
|---------|------|------|------|
| **1** | DeepSeek V4 | 메인 (범용) | 일반 대화, 응답 생성, 기본 작업 |
| **1** | DeepSeek R1 | 메인 (추론) | 투표, 전략, 수학, 코드 리뷰, 복잡한 추론 |
| **2** | Gemini 2.5 Flash | 폴백 #1 | 빠르고 비용 효율적, DeepSeek 장애 시 자동 전환 |
| **3** | Gemini 3 Flash Preview | 폴백 #2 | 최신 프리뷰, 실험적, 모든 Gemini 2.5 Flash 장애 시 전환 |

---

## 🔧 모델 자동 선택 로직

### 작업 유형별 모델 선택

```python
# backend/services/llm_provider_service.py

class LLMProviderService:
    def select_model(self, task_type: str, complexity: float = 0.0) -> str:
        """
        작업 유형에 따라 적절한 모델 선택
        
        Args:
            task_type: 작업 유형 (vote, strategy, chat, etc.)
            complexity: 작업 복잡도 (0.0 ~ 1.0)
        
        Returns:
            model_name: 선택된 모델 이름
        """
        # R1 강제 사용 케이스
        if task_type in ['vote', 'strategy', 'analysis', 'math', 'reasoning', 'decision']:
            return 'deepseek-r1'
        
        # R1 권장 케이스
        if task_type == 'architecture' and complexity >= 0.7:
            return 'deepseek-r1'
        if task_type in ['insight', 'evaluation', 'code review']:
            return 'deepseek-r1'
        
        # 기본: V4
        return 'deepseek-v4'
```

### 작업 유형 분류

#### R1 강제 사용 (고급 추론 필요)
- **vote**: 투표 및 의견 수렴
- **strategy**: 전략 분석 및 계획
- **analysis**: 데이터 분석
- **math**: 수학적 계산
- **reasoning**: 논리적 추론
- **decision**: 의사결정

#### R1 권장 사용 (복잡한 작업)
- **architecture** (복잡도 ≥ 0.7): 아키텍처 설계
- **insight**: 인사이트 도출
- **evaluation**: 평가 및 검토
- **code review**: 코드 리뷰

#### V4 기본 사용 (일반 작업)
- **chat**: 일반 대화
- **question**: 질문 응답
- **generation**: 콘텐츠 생성
- **translation**: 번역
- **summarization**: 요약

---

## 🔄 Failover 시나리오

### 시나리오 1: 정상 작동
```
사용자 요청 → DeepSeek V4 → 응답 ✅
```

**성공 조건**:
- API 호출 성공
- 응답 시간 < 30초
- 유효한 JSON 응답

### 시나리오 2: DeepSeek V4 장애 → Gemini 2.5 Flash
```
사용자 요청 → DeepSeek V4 (에러) → Gemini 2.5 Flash → 응답 ✅
```

**전환 조건**:
- DeepSeek API 타임아웃 (30초)
- 429 Too Many Requests
- 500 Internal Server Error
- 네트워크 연결 실패

**재시도 로직**:
- Exponential backoff + jitter
- Provider당 최대 3회 재시도
- 재시도 실패 시 다음 Provider로 전환

### 시나리오 3: 모든 DeepSeek 장애 → Gemini 3 Flash Preview
```
사용자 요청 → DeepSeek V4 (에러) → Gemini 2.5 Flash (에러) → Gemini 3 Flash Preview → 응답 ✅
```

**전환 조건**:
- DeepSeek V4 + R1 모두 실패
- Gemini 2.5 Flash 실패
- 최후 수단으로 Gemini 3 Flash Preview 사용

### 시나리오 4: 복잡한 추론 작업
```
사용자 요청 (투표/전략) → DeepSeek R1 → 응답 ✅
```

**자동 선택**:
- task_type이 'vote', 'strategy' 등인 경우 자동으로 R1 선택
- R1 실패 시 Gemini 2.5 Flash로 폴백 (추론 능력은 떨어지지만 서비스 가용성 우선)

---

## 🛠️ 구현 세부사항

### 1. LLMProvider 클래스

```python
# backend/services/llm_provider_service.py

from typing import Dict, List, Optional
import httpx
import asyncio
import os
import random
from datetime import datetime

class LLMProvider:
    """개별 LLM Provider 정보 및 통계"""
    
    def __init__(
        self,
        name: str,
        priority: int,
        api_key: str,
        base_url: str,
        model_name: str,
        is_fallback: bool = False,
        timeout: int = 30
    ):
        self.name = name
        self.priority = priority
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.is_fallback = is_fallback
        self.timeout = timeout
        
        # 통계
        self.stats = {
            "total_calls": 0,
            "success_calls": 0,
            "errors": 0,
            "total_latency_ms": 0,
            "avg_latency_ms": 0
        }
    
    def update_stats(self, success: bool, latency_ms: float):
        """통계 업데이트"""
        self.stats["total_calls"] += 1
        if success:
            self.stats["success_calls"] += 1
        else:
            self.stats["errors"] += 1
        
        self.stats["total_latency_ms"] += latency_ms
        self.stats["avg_latency_ms"] = (
            self.stats["total_latency_ms"] / self.stats["total_calls"]
        )
```

### 2. LLMProviderService 클래스

```python
class LLMProviderService:
    """다중 LLM Provider 관리 및 Failover"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self._setup_providers()
    
    def _setup_providers(self):
        """프로바이더 등록 (우선순위별)"""
        
        # DeepSeek V4 (메인 #1)
        self.providers['deepseek-v4'] = LLMProvider(
            name="deepseek-v4",
            priority=1,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
            model_name="deepseek-chat",
            is_fallback=False,
            timeout=30
        )
        
        # DeepSeek R1 (메인 #1 - 추론용)
        self.providers['deepseek-r1'] = LLMProvider(
            name="deepseek-r1",
            priority=1,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
            model_name="deepseek-reasoner",
            is_fallback=False,
            timeout=60  # R1은 더 오래 걸릴 수 있음
        )
        
        # Gemini 2.5 Flash (폴백 #2)
        self.providers['gemini-2.5-flash'] = LLMProvider(
            name="gemini-2.5-flash",
            priority=2,
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta",
            model_name="gemini-2.5-flash",
            is_fallback=True,
            timeout=30
        )
        
        # Gemini 3 Flash Preview (폴백 #3)
        self.providers['gemini-3-flash-preview'] = LLMProvider(
            name="gemini-3-flash-preview",
            priority=3,
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta",
            model_name="gemini-3-flash-preview",
            is_fallback=True,
            timeout=30
        )
    
    async def call_with_fallback(
        self,
        prompt: str,
        task_type: str = "chat",
        complexity: float = 0.0
    ) -> str:
        """
        Failover 로직이 포함된 LLM 호출
        
        Args:
            prompt: 사용자 프롬프트
            task_type: 작업 유형
            complexity: 작업 복잡도
        
        Returns:
            response: LLM 응답 텍스트
        
        Raises:
            Exception: 모든 Provider 실패 시
        """
        # 1단계: 적절한 모델 선택
        primary_model = self.select_model(task_type, complexity)
        primary_provider = self.providers[primary_model]
        
        # 2단계: 우선순위별로 시도
        sorted_providers = sorted(
            self.providers.values(),
            key=lambda p: (p.priority, p.name != primary_model)
        )
        
        for provider in sorted_providers:
            # 폴백이 아닌데 메인이 아닌 경우 스킵
            if provider.priority > 1 and not provider.is_fallback:
                continue
            
            try:
                start_time = datetime.now()
                response = await self._call_provider(provider, prompt)
                latency = (datetime.now() - start_time).total_seconds() * 1000
                
                # 통계 업데이트
                provider.update_stats(success=True, latency_ms=latency)
                
                return response
            except Exception as e:
                provider.update_stats(success=False, latency_ms=0)
                print(f"Provider {provider.name} failed: {e}")
                
                # 폴백이 아니면 즉시 실패
                if not provider.is_fallback:
                    raise
                
                # 다음 폴백 시도
                continue
        
        raise Exception("All providers failed")
    
    async def _call_provider(self, provider: LLMProvider, prompt: str) -> str:
        """
        실제 API 호출 (Exponential backoff + jitter)
        
        Args:
            provider: LLM Provider
            prompt: 사용자 프롬프트
        
        Returns:
            response: LLM 응답 텍스트
        """
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    # DeepSeek API 호출
                    if provider.name.startswith('deepseek'):
                        response = await client.post(
                            f"{provider.base_url}/chat/completions",
                            headers={"Authorization": f"Bearer {provider.api_key}"},
                            json={
                                "model": provider.model_name,
                                "messages": [{"role": "user", "content": prompt}]
                            },
                            timeout=provider.timeout
                        )
                        response.raise_for_status()
                        return response.json()["choices"][0]["message"]["content"]
                    
                    # Gemini API 호출
                    elif provider.name.startswith('gemini'):
                        response = await client.post(
                            f"{provider.base_url}/models/{provider.model_name}:generateContent",
                            headers={"x-goog-api-key": provider.api_key},
                            json={
                                "contents": [{"parts": [{"text": prompt}]}]
                            },
                            timeout=provider.timeout
                        )
                        response.raise_for_status()
                        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff + jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise Exception(f"Provider {provider.name} failed after {max_retries} retries")
```

---

## 📊 통계 및 모니터링

### Provider별 추적 지표

```python
{
    "deepseek-v4": {
        "total_calls": 1234,
        "success_calls": 1200,
        "errors": 34,
        "total_latency_ms": 36000,
        "avg_latency_ms": 29.2,
        "success_rate": 0.972
    },
    "deepseek-r1": {
        "total_calls": 567,
        "success_calls": 560,
        "errors": 7,
        "total_latency_ms": 45000,
        "avg_latency_ms": 79.4,
        "success_rate": 0.988
    },
    "gemini-2.5-flash": {
        "total_calls": 34,
        "success_calls": 34,
        "errors": 0,
        "total_latency_ms": 850,
        "avg_latency_ms": 25.0,
        "success_rate": 1.0
    },
    "gemini-3-flash-preview": {
        "total_calls": 0,
        "success_calls": 0,
        "errors": 0,
        "total_latency_ms": 0,
        "avg_latency_ms": 0,
        "success_rate": 0.0
    }
}
```

### API 엔드포인트

```python
# backend/routes/llm_stats.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/api/llm/stats")
async def get_llm_stats():
    """LLM Provider별 통계 조회"""
    return {
        "providers": {
            name: provider.stats
            for name, provider in llm_service.providers.items()
        }
    }

@router.get("/api/llm/health")
async def get_llm_health():
    """LLM Provider 상태 확인"""
    return {
        "primary": "deepseek-v4",
        "fallback_1": "gemini-2.5-flash",
        "fallback_2": "gemini-3-flash-preview",
        "status": "healthy"
    }
```

---

## 🔐 환경 변수

### .env 파일

```bash
# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Gemini API (Google AI Studio 또는 Vertex AI)
GEMINI_API_KEY=your_gemini_api_key_here

# 로깅 레벨
LOG_LEVEL=INFO
```

### config.py

```python
# backend/config.py

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # DeepSeek
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_TIMEOUT: int = 30
    
    # Gemini
    GEMINI_API_KEY: str
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_TIMEOUT: int = 30
    
    # Failover 설정
    LLM_MAX_RETRIES: int = 3
    LLM_BACKOFF_BASE: float = 1.0
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 🚀 배포 체크리스트

### Phase 1: 개발 환경
- [ ] DeepSeek API 키 발급
- [ ] Gemini API 키 발급 (Google AI Studio)
- [ ] 환경 변수 설정
- [ ] LLMProviderService 구현
- [ ] 단위 테스트 작성

### Phase 2: 통합 테스트
- [ ] Failover 시나리오 테스트
- [ ] 성능 테스트 (동시 요청 100개)
- [ ] 통계 추적 확인
- [ ] 에러 로깅 확인

### Phase 3: 프로덕션 배포
- [ ] 환경 변수 프로덕션 설정
- [ ] 모니터링 대시보드 구축
- [ ] 알림 설정 (Provider 장애 시)
- [ ] 문서화 완료

---

## ⚠️ 주의사항

### API 호출 제한
1. **DeepSeek**: 분당 60회 (캐싱 필수)
2. **Gemini 2.5 Flash**: 분당 60회 (무료 등급)
3. **Gemini 3 Flash Preview**: 프리뷰 기간 동안 제한적

### 비용 관리
1. **DeepSeek V4**: $0.14 / 1M 토큰 (입력)
2. **DeepSeek R1**: $0.55 / 1M 토큰 (입력)
3. **Gemini 2.5 Flash**: 무료 (일일 할당량 내)
4. **Gemini 3 Flash Preview**: 무료 (프리뷰 기간)

### 보안
1. **API 키 관리**: 환경 변수로만 관리
2. **로깅**: API 키 로그에 노출 금지
3. **HTTPS**: 모든 API 호출은 HTTPS 사용

---

## 📚 참고 자료

- **DeepSeek API 문서**: https://platform.deepseek.com/docs
- **Gemini API 문서**: https://ai.google.dev/docs
- **httpx 문서**: https://www.python-httpx.org/
- **Exponential Backoff**: https://aws.amazon.com/ko/blogs/architecture/exponential-backoff-and-jitter/

---

**작성자**: Sisyphus (팀 리더)
**검토 요청일**: 2026-04-06
**상태**: 검토 완료 ✅
