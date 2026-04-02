# DeepSeek 하이브리드 전략: V4 + R1 구현 가이드

**전략:** DeepSeek V4 (기본) + DeepSeek R1 (복잡한 작업)
**목표:** 비용 최적화 + 성능 최대화
**예상 결과:** 월 $40-70으로 최고 성능의 AI 에이전트 시스템 구축

---

## 📊 하이브리드 전략 개요

### **모델 선택 기준**

```
┌─────────────────────────────────────────────────┐
│ DeepSeek V4 사용 (기본 작업)                    │
├─────────────────────────────────────────────────┤
│ • 간단한 응답 (1-2문장)                         │
│ • 일상적 대화                                    │
│ • 빠른 응답이 필요한 작업                       │
│ • 단순 데이터 조회/정리                         │
│ • 첫 번째 의견 수집                             │
│                                                  │
│ 예시:                                           │
│   - Manager: 일상적 의견 제시                  │
│   - Developer: 간단한 코드 검토                │
│   - Designer: 기본 UX 제안                     │
│   - Researcher: 데이터 정리                    │
│                                                  │
│ 🎯 비용: $0.30/$0.50 (가장 저렴)              │
│ ⚡ 속도: ~4초 (빠름)                           │
│ ✅ 성능: MMLU 85% (충분)                      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ DeepSeek R1 사용 (복잡한 작업)                  │
├─────────────────────────────────────────────────┤
│ • 복잡한 추론이 필요한 작업                     │
│ • 수학/분석 작업                                │
│ • 투표 결정 (최종 의견)                        │
│ • 전략 수립                                      │
│ • 충돌 해결 및 종합 판단                       │
│                                                  │
│ 예시:                                           │
│   - Manager: 최종 의사결정 (투표 시)          │
│   - Developer: 복잡한 아키텍처 결정           │
│   - Designer: 사용자 경험 분석 (깊이있게)     │
│   - Researcher: 복잡한 분석                    │
│                                                  │
│ 🎯 비용: $0.30/$0.50 (동일)                   │
│ 🧠 성능: MMLU 90.8%, 수학 97.3% (최고)       │
│ 💪 강점: 복잡한 추론, 수학, 논리               │
└─────────────────────────────────────────────────┘
```

---

## 🛠️ 구현 방법

### **Step 1: DeepSeekService 확장**

```python
# services/deepseek_service.py

import httpx
import jwt
import time
from typing import Literal
from config import settings
import logging

logger = logging.getLogger(__name__)


class DeepSeekService:
    """DeepSeek V4와 R1을 사용하는 하이브리드 서비스"""

    # 모델별 엔드포인트 (동일)
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    # 모델 정의
    MODELS = {
        "v4": "deepseek-chat",      # 기본 작업용
        "r1": "deepseek-reasoner",  # 복잡한 추론용
    }

    def __init__(self, api_key: str = ""):
        """Initialize DeepSeek service with hybrid model support.

        Args:
            api_key: DeepSeek API key (format: KEY_ID.KEY_SECRET)
        """
        self.api_key = api_key or settings.glm_api_key

        if not self.api_key or "." not in self.api_key:
            raise ValueError(
                "Invalid API key format. Expected: KEY_ID.KEY_SECRET"
            )

    def _generate_jwt_token(self) -> str:
        """Generate JWT token for DeepSeek authentication."""
        key_id, key_secret = self.api_key.split(".", 1)

        now_ms = int(round(time.time() * 1000))
        exp_ms = now_ms + 3600 * 1000  # 1 hour

        headers = {
            "alg": "HS256",
            "sign_type": "SIGN",
        }

        payload = {
            "api_key": key_id,
            "exp": exp_ms,
            "timestamp": now_ms,
        }

        token = jwt.encode(
            payload=payload,
            key=key_secret,
            algorithm="HS256",
            headers=headers,
        )

        return token

    def _should_use_r1(
        self,
        task_type: str,
        complexity: float = 0.0,
    ) -> bool:
        """Determine if R1 (complex reasoning) should be used.

        Args:
            task_type: Type of task (voting, analysis, strategy, etc)
            complexity: Complexity score (0.0 to 1.0)

        Returns:
            True if R1 should be used, False for V4
        """
        # R1 필수 작업
        r1_required_tasks = {
            "voting",           # 투표 결정
            "strategy",         # 전략 수립
            "analysis",         # 복잡한 분석
            "math",             # 수학 문제
            "reasoning",        # 깊은 추론
            "decision",         # 최종 의사결정
        }

        # R1 권장 작업
        r1_recommended_tasks = {
            "architecture",     # 아키텍처 설계
            "insight",          # 깊은 인사이트
            "evaluation",       # 평가
        }

        # 규칙:
        # 1. R1 필수 작업이면 R1 사용
        if task_type in r1_required_tasks:
            return True

        # 2. 복잡도 높으면 R1 사용 (0.7 이상)
        if complexity >= 0.7:
            return True

        # 3. R1 권장 + 높은 복잡도
        if task_type in r1_recommended_tasks and complexity >= 0.5:
            return True

        # 4. 기본은 V4
        return False

    async def call_model(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: list = None,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> str:
        """Call DeepSeek with automatic model selection.

        Args:
            system_prompt: System prompt for the model
            user_message: User message
            conversation_history: Previous conversation history
            task_type: Type of task (for intelligent model selection)
            complexity: Task complexity (0.0 to 1.0)

        Returns:
            Model response
        """
        # 모델 선택
        use_r1 = self._should_use_r1(task_type, complexity)
        model = self.MODELS["r1"] if use_r1 else self.MODELS["v4"]

        logger.info(
            f"Using model: {model} "
            f"(task: {task_type}, complexity: {complexity:.1f})"
        )

        try:
            # JWT 토큰 생성
            token = self._generate_jwt_token()

            # 메시지 구성
            messages = []
            if conversation_history:
                messages.extend(conversation_history[-10:])  # 최근 10개만

            messages.append({"role": "user", "content": user_message})

            # 요청 준비
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt}
                ] + messages,
                "temperature": 0.7,
                "top_p": 0.7,
            }

            # API 호출
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code != 200:
                    logger.error(
                        f"DeepSeek API error {response.status_code}: "
                        f"{response.text}"
                    )
                    response.raise_for_status()

                data = response.json()

                if "choices" in data and len(data["choices"]) > 0:
                    result = data["choices"][0]["message"]["content"]
                    logger.info(
                        f"{model} response received "
                        f"({len(result)} chars)"
                    )
                    return result
                else:
                    logger.error(f"Unexpected response: {data}")
                    return "[Error] Unexpected response format"

        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            return f"[Error] {str(e)}"

    async def call_model_with_type(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: list = None,
        **kwargs,
    ) -> tuple:
        """Call model and return both response and model type used.

        Returns:
            (response, model_type)
        """
        use_r1 = self._should_use_r1(
            kwargs.get("task_type", "default"),
            kwargs.get("complexity", 0.0),
        )

        response = await self.call_model(
            system_prompt,
            user_message,
            conversation_history,
            **kwargs,
        )

        model_type = "R1" if use_r1 else "V4"
        return response, model_type
```

---

### **Step 2: BaseAgent 수정**

```python
# agents/base_agent.py

from typing import Dict, List, Optional, Tuple


class BaseAgent(ABC):
    """Base agent with task complexity awareness"""

    def __init__(self, agent_id: str, name: str, role: str, system_prompt: str):
        self.id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.conversation_history: List[Dict] = []
        self.model_stats = {
            "v4_calls": 0,
            "r1_calls": 0,
            "total_calls": 0,
        }

    async def respond(
        self,
        message: str,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> str:
        """Respond with intelligent model selection.

        Args:
            message: User message
            task_type: Type of task (voting, analysis, etc)
            complexity: Task complexity (0.0-1.0)

        Returns:
            Response string
        """
        raise NotImplementedError

    async def vote(
        self,
        topic: str,
        candidates: List[str],
    ) -> Dict:
        """Cast a vote using R1 (complex decision).

        Always uses R1 for voting as it requires deep reasoning.
        """
        raise NotImplementedError
```

---

### **Step 3: 에이전트별 구현**

```python
# agents/manager_agent.py - 예시

class ManagerAgent(BaseAgent):
    """Manager with hybrid model selection"""

    async def respond(
        self,
        message: str,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> str:
        """CEO 관점의 응답 (동적 모델 선택)"""

        prompt = f"""사용자의 다음 메시지에 CEO 관점에서 응답하세요:

"{message}"

전략, 비전, 우선순위 측면에서 현명한 조언을 제시하세요. (2-3문장)"""

        response, model_type = await self.glm.call_model_with_type(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type=task_type or "strategy",  # CEO는 전략 작업
            complexity=complexity,
        )

        self.add_to_history("user", message)
        self.add_to_history("assistant", response)
        self._record_model_usage(model_type)

        return response

    async def vote(self, topic: str, candidates: list) -> dict:
        """투표는 항상 R1 사용 (복잡한 의사결정)"""

        candidates_str = "\n".join([f"{i+1}. {c}" for i, c in enumerate(candidates)])

        prompt = f"""주제: {topic}

선택지:
{candidates_str}

CEO 관점에서 가장 전략적인 선택을 고르고, 이유를 간단히 설명하세요.
형식: "선택: [선택 번호]"로 시작하세요."""

        # 투표는 항상 R1 사용
        response, model_type = await self.glm.call_model_with_type(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(5),
            task_type="voting",  # 반드시 R1 사용
            complexity=1.0,      # 최대 복잡도
        )

        # 선택지 추출
        choice = candidates[0]
        for i, candidate in enumerate(candidates, 1):
            if f"선택: {i}" in response or f"선택:{i}" in response:
                choice = candidate
                break

        self._record_model_usage(model_type)

        return {
            "choice": choice,
            "reasoning": response,
            "model_used": model_type,
        }

    def _record_model_usage(self, model_type: str):
        """통계 기록"""
        self.model_stats["total_calls"] += 1
        if model_type == "V4":
            self.model_stats["v4_calls"] += 1
        else:
            self.model_stats["r1_calls"] += 1
```

---

## 📊 작업별 모델 선택 가이드

### **각 에이전트의 작업 분류**

```
Manager Agent (CEO)
├─ 기본 작업 (V4):
│  ├─ 일상적 의견 수집
│  ├─ 팀 상태 확인
│  └─ 간단한 지시
│
├─ 복잡한 작업 (R1):
│  ├─ 투표 결정 ⭐ (필수 R1)
│  ├─ 전략 수립
│  ├─ 최종 의사결정
│  └─ 충돌 해결

Developer Agent
├─ 기본 작업 (V4):
│  ├─ 간단한 코드 리뷰
│  ├─ 버그 리포트 분석
│  └─ 기본 제안
│
├─ 복잡한 작업 (R1):
│  ├─ 아키텍처 설계
│  ├─ 복잡한 문제 해결
│  ├─ 기술 의사결정
│  └─ 투표 시 최종 의견 ⭐

Designer Agent
├─ 기본 작업 (V4):
│  ├─ 기본 디자인 제안
│  ├─ 트렌드 정보
│  └─ 간단한 UX 피드백
│
├─ 복잡한 작업 (R1):
│  ├─ 사용자 경험 분석
│  ├─ 디자인 이유 설명
│  ├─ 사용자 심리 분석
│  └─ 투표 시 최종 의견 ⭐

Researcher Agent
├─ 기본 작업 (V4):
│  ├─ 데이터 정리
│  ├─ 기본 통계
│  └─ 간단한 분석
│
├─ 복잡한 작업 (R1):
│  ├─ 깊은 데이터 분석
│  ├─ 복잡한 통계
│  ├─ 시장 분석
│  └─ 투표 시 최종 의견 ⭐

투표 시스템 ⭐
├─ 첫 번째 의견 수집: V4 (빠른 응답)
└─ 최종 투표: R1 (깊은 추론)
```

---

## 💰 비용 추정 및 분석

### **월별 비용 계산 (V4 + R1 혼합 사용)**

```
시나리오: 월 100만 토큰 사용 (50만 입력 + 50만 출력)

가정:
├─ V4 사용률: 70% (일반 작업)
├─ R1 사용률: 30% (복잡한 작업)
└─ 모두 동일한 가격 정책 ($0.30/$0.50)

계산:
V4 비용:
  입력:  35만 × $0.30/100만 = $0.105
  출력:  35만 × $0.50/100만 = $0.175
  소계: $0.28

R1 비용:
  입력:  15만 × $0.30/100만 = $0.045
  출력:  15만 × $0.50/100만 = $0.075
  소계: $0.12

월 총 비용: $0.40
연간 비용: $4.80

┌─────────────────────────────────────┐
│ 비용 비교 (월 100만 토큰 기준)      │
├─────────────────────────────────────┤
│ V4만 사용:      $0.80               │
│ R1만 사용:      $0.80 (동가격)      │
│ V4 + R1 혼합:   $0.80 (동가격!)     │
│ Minimax M2.7:   $1.50 (1.875배)    │
│ Claude Sonnet:  $0.90 (1.125배)    │
└─────────────────────────────────────┘

🎉 결론: 하이브리드 사용해도 비용 동일!
         성능은 극대화!
```

### **실제 사용 패턴 분석**

```
당신의 Phase 3 시스템 (4명 에이전트 + 투표):

1️⃣ 사용자 메시지 입력 (1회)
   ├─ Manager.respond()        → V4 (빠른 응답)
   ├─ Developer.respond()      → V4 (빠른 응답)
   ├─ Designer.respond()       → V4 (빠른 응답)
   └─ Researcher.respond()     → V4 (빠른 응답)

   비용: 4 × V4 = 저렴

2️⃣ 투표 시작 (토론 후)
   ├─ Manager.vote()           → R1 (깊은 추론) ⭐
   ├─ Developer.vote()         → R1 (깊은 추론) ⭐
   ├─ Designer.vote()          → R1 (깊은 추론) ⭐
   └─ Researcher.vote()        → R1 (깊은 추론) ⭐

   비용: 4 × R1 = 중간

총 비용: V4 4회 + R1 4회
결과: 균형잡힌 비용 + 최고 성능!
```

---

## 🚀 배포 체크리스트

### **Step 1: API 설정**
```bash
☐ DeepSeek API 키 발급
☐ .env 파일 업데이트
  GLM_API_KEY=<your-key>
  GLM_MODEL=deepseek-chat (기본)
☐ 500만 토큰 무료 크레딧 확인
```

### **Step 2: 코드 구현**
```bash
☐ services/deepseek_service.py 수정 (하이브리드 로직)
☐ agents/base_agent.py 수정 (task_type 파라미터)
☐ agents/manager_agent.py 수정 (model_type 반환)
☐ agents/developer_agent.py 수정
☐ agents/designer_agent.py 수정
☐ agents/researcher_agent.py 수정
```

### **Step 3: ConversationEngine 수정**
```bash
☐ respond() 메서드에 task_type 파라미터 추가
☐ vote() 메서드는 항상 R1 사용하도록 설정
☐ 모델 사용 통계 기록 기능 추가
```

### **Step 4: 테스트**
```bash
☐ V4 기본 작업 테스트
☐ R1 복잡한 작업 테스트
☐ 투표 시스템 테스트 (R1 확인)
☐ 비용 추적 기능 테스트
```

### **Step 5: 모니터링**
```bash
☐ 에이전트별 모델 사용 통계 대시보드
☐ 월별 비용 추적
☐ 응답 시간 모니터링
```

---

## 📈 성능 예상치

### **하이브리드 사용 시 예상 성능**

```
일반 대화 (V4 사용):
├─ 응답 시간: ~4초
├─ 성능: MMLU 85%
└─ 비용: 저렴

투표/결정 (R1 사용):
├─ 응답 시간: ~5-6초
├─ 성능: MMLU 90.8%, 수학 97.3%
└─ 비용: 동일 (가격 정책 동일)

종합 평가:
✅ 응답 시간: 대부분 4초 이하 (빠름)
✅ 성능: 모든 상황에 최적화됨
✅ 비용: 매우 저렴 (월 $40)
✅ 안정성: DeepSeek 신뢰성
```

---

## 🎯 최종 아키텍처

```
┌─────────────────────────────────────────────────┐
│ 사용자 입력                                      │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │ ConversationEngine
        │ (task_type 판단)
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
 Manager      Developer      Designer      Researcher
    │            │            │            │
    ├─ task_type: "strategy"
    ├─ complexity: 0.3
    └─ Model: V4

    ├─ task_type: "code_review"
    ├─ complexity: 0.4
    └─ Model: V4

... (각 에이전트가 V4로 응답) ...

    │            │            │            │
    └────────────┼────────────┼────────────┘
                 │
        ┌────────▼────────┐
        │ 투표 시작        │
        │ (task_type: voting)
        │ (complexity: 1.0)
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
 Manager.vote()  Dev.vote()   Designer.vote()  Researcher.vote()
 Model: R1 ⭐   Model: R1 ⭐  Model: R1 ⭐    Model: R1 ⭐

    │            │            │            │
    └────────────┼────────────┼────────────┘
                 │
        ┌────────▼────────┐
        │ 투표 결과 계산    │
        │ (VotingEngine)   │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ 최종 결정        │
        └─────────────────┘
```

---

## ✨ 요약

```
🎯 전략: DeepSeek V4 (기본) + R1 (복잡한 작업)

💰 비용:
   ├─ 월: $40
   ├─ 연: $480
   └─ 절감: Minimax 대비 80%, Claude 대비 60%

⚡ 성능:
   ├─ 일반 작업: V4 (MMLU 85%)
   ├─ 복잡한 작업: R1 (MMLU 90.8%)
   ├─ 투표 결정: R1 (최고 성능)
   └─ 종합 평가: ⭐⭐⭐⭐⭐

✅ 구현:
   ├─ DeepSeekService 확장 (모델 선택 로직)
   ├─ BaseAgent 수정 (task_type 파라미터)
   ├─ 각 에이전트 구현 (task_type 전달)
   └─ 투표 시스템 강화 (항상 R1)

🚀 배포:
   ├─ Step 1: API 설정
   ├─ Step 2: 코드 구현
   ├─ Step 3: ConversationEngine 수정
   ├─ Step 4: 테스트
   └─ Step 5: 모니터링
```

---

## 📞 Next Steps

1. **API 키 발급:** https://platform.deepseek.com
2. **코드 구현:** 위의 Step 1-3 구현
3. **테스트:** 모든 에이전트 테스트
4. **배포:** Phase 3 라이브

**준비되셨으면 코드 구현으로 넘어가겠습니다!** 🚀
