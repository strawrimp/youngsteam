"""
SharedContextBuilder: 대화 컨텍스트를 에이전트에게 전달하기 위한 빌더.

세 가지 컨텍스트를 생성합니다:
1. Live Context — 현재 대화의 최근 메시지 (모든 에이전트 발언 포함)
2. Referenced Context — 사용자가 #C-YYMMDD-NNN 참조 코드를 언급한 경우 해당 대화
3. Past Conversation Context — 자연어 시간 키워드("어제", "지난주" 등)로 과거 대화 검색
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from database import SessionLocal
from models import Conversation, Message, Agent

logger = logging.getLogger(__name__)

# 참조 코드 패턴: #C-YYMMDD-NNN
REFERENCE_CODE_PATTERN = re.compile(r"#C-(\d{6})-(\d{3})")

# 시간 키워드 → 날짜 범위 매핑
TIME_KEYWORD_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("어제", re.compile(r"어제")),
    ("그제", re.compile(r"그제")),
    ("오늘", re.compile(r"오늘")),
    ("지난주", re.compile(r"지난\s*주")),
    ("저번주", re.compile(r"저번\s*주")),
    ("지난달", re.compile(r"지난\s*달")),
    ("저번달", re.compile(r"저번\s*달")),
    ("최근", re.compile(r"최근")),
    ("이전에", re.compile(r"이전에?")),
    ("과거에", re.compile(r"과거에?")),
    ("예전에", re.compile(r"예전에?")),
    ("저번에", re.compile(r"저번에?")),
    ("지난번", re.compile(r"지난\s*번")),
    ("며칠 전", re.compile(r"며칠\s*전")),
]

# 시간 표현에서 제외할 불용어 (검색 키워드 추출 시)
TIME_STOPWORDS = {
    "어제",
    "그제",
    "오늘",
    "지난주",
    "저번주",
    "지난달",
    "저번달",
    "최근",
    "이전에",
    "이전",
    "과거에",
    "과거",
    "예전에",
    "예전",
    "저번에",
    "저번",
    "지난번",
    "지난",
    "며칠전",
    "며칠",
    "대화",
    "내용",
    "브리핑",
    "요약",
    "알려줘",
    "말해줘",
    "보여줘",
    "부탁해",
    "해줘",
    "해주세요",
    "부탁드립니다",
    "브리핑해줘",
    "알려주세요",
    "정리해줘",
    "요약해줘",
    "말해주세요",
    "정리해주세요",
    "브리핑해",
    "요약해",
    "정리해",
    "주세요",
    "해라",
    "합니다",
    "입니다",
    "있는",
    "관한",
    "에서",
    "논의한",
    "논의",
    "이야기",
    "얘기",
    "지난주에",
    "저번주에",
}


def detect_reference_codes(text: str) -> List[str]:
    """텍스트에서 참조 코드를 감지합니다.

    Args:
        text: 사용자 메시지

    Returns:
        감지된 참조 코드 리스트 (예: ["#C-260414-003"])
    """
    matches = REFERENCE_CODE_PATTERN.findall(text)
    return [f"#C-{date}-{seq}" for date, seq in matches]


def build_live_context(
    conversation_id: str,
    limit: int = 20,
) -> str:
    """현재 대화의 최근 메시지를 포맷된 컨텍스트로 반환합니다.

    모든 에이전트의 발언을 포함하여 "누가 무슨 말을 했는지" 파악 가능합니다.

    Args:
        conversation_id: 대화 ID
        limit: 가져올 최대 메시지 수

    Returns:
        포맷된 대화 컨텍스트 문자열 (빈 문자열 가능)
    """
    db = SessionLocal()
    try:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

        if not messages:
            return ""

        # 오래된 순으로 정렬 (desc로 가져왔으므로 reverse)
        messages = list(reversed(messages))

        # 에이전트 ID → 표시명 매핑 캐시
        agent_cache: Dict[str, str] = {}

        lines = []
        for msg in messages:
            if msg.sender_type == "user":
                lines.append(f"👤 사용자: {msg.content}")
            elif msg.sender_type == "agent":
                agent_display = _get_agent_display(db, agent_cache, msg.agent_id)
                lines.append(f"🤖 {agent_display}: {msg.content}")
            else:
                lines.append(f"📋 시스템: {msg.content}")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"[SharedContext] build_live_context error: {e}")
        return ""
    finally:
        db.close()


def build_referenced_context(reference_codes: List[str]) -> str:
    """참조 코드에 해당하는 대화 내용을 로드합니다.

    Args:
        reference_codes: 참조 코드 리스트 (예: ["#C-260414-003"])

    Returns:
        포맷된 참조 대화 문자열
    """
    if not reference_codes:
        return ""

    db = SessionLocal()
    try:
        parts = []

        for code in reference_codes:
            conv = (
                db.query(Conversation)
                .filter(Conversation.reference_code == code)
                .first()
            )
            if not conv:
                parts.append(f"[{code}] 해당 참조 코드의 대화를 찾을 수 없습니다.")
                continue

            # 대화 메타 정보
            header = f"[{code}] 제목: {conv.title or '제목 없음'}"
            if conv.category:
                header += f" | 분류: {conv.category}"
            if conv.summary:
                header += f"\n요약: {conv.summary}"

            # 대화 메시지
            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
                .all()
            )

            agent_cache: Dict[str, str] = {}
            msg_lines = []
            for msg in messages:
                if msg.sender_type == "user":
                    msg_lines.append(f"  👤 사용자: {_truncate(msg.content, 200)}")
                elif msg.sender_type == "agent":
                    agent_display = _get_agent_display(db, agent_cache, msg.agent_id)
                    msg_lines.append(
                        f"  🤖 {agent_display}: {_truncate(msg.content, 200)}"
                    )

            parts.append(header + "\n" + "\n".join(msg_lines))

        return "\n\n".join(parts)

    except Exception as e:
        logger.error(f"[SharedContext] build_referenced_context error: {e}")
        return ""
    finally:
        db.close()


def generate_reference_code() -> str:
    """당일 순차 참조 코드를 생성합니다.

    포맷: #C-YYMMDD-NNN
    예: #C-260414-001

    Returns:
        새 참조 코드
    """
    db = SessionLocal()
    try:
        today_prefix = datetime.now().strftime("#C-%y%m%d-")

        # 당일 최대 번호 조회
        latest = (
            db.query(Conversation.reference_code)
            .filter(Conversation.reference_code.like(f"{today_prefix}%"))
            .order_by(Conversation.reference_code.desc())
            .first()
        )

        if latest and latest[0]:
            # 마지막 3자리 추출 → +1
            last_num = int(latest[0].split("-")[-1])
            next_num = last_num + 1
        else:
            next_num = 1

        return f"{today_prefix}{next_num:03d}"

    except Exception as e:
        logger.error(f"[SharedContext] generate_reference_code error: {e}")
        # 폴백: 타임스탬프 기반
        return f"#C-{datetime.now().strftime('%y%m%d')}-{int(datetime.now().timestamp()) % 1000:03d}"
    finally:
        db.close()


def _get_agent_display(db, cache: Dict[str, str], agent_id: Optional[str]) -> str:
    """에이전트 ID → 표시명 (예: "네오/비서실장")"""
    if not agent_id:
        return "에이전트"

    if agent_id not in cache:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if agent:
            cache[agent_id] = agent.display_name or agent.name
        else:
            cache[agent_id] = "에이전트"

    return cache[agent_id]


def _truncate(text: str, max_len: int = 200) -> str:
    """텍스트를 max_len으로 자르기"""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def detect_natural_time_reference(text: str) -> Optional[Dict]:
    """사용자 메시지에서 자연어 시간 키워드를 감지하여 날짜 범위를 반환합니다.

    Args:
        text: 사용자 메시지

    Returns:
        {"date_from": str, "date_to": str, "keywords": List[str], "time_keyword": str}
        또는 None (시간 키워드가 없는 경우)
    """
    now = datetime.now()
    date_from = None
    date_to = None
    matched_keyword = None

    for keyword, pattern in TIME_KEYWORD_PATTERNS:
        if pattern.search(text):
            matched_keyword = keyword
            if keyword == "어제":
                date_from = (now - timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                date_to = (now - timedelta(days=1)).replace(
                    hour=23, minute=59, second=59, microsecond=0
                )
            elif keyword == "그제":
                date_from = (now - timedelta(days=2)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                date_to = (now - timedelta(days=2)).replace(
                    hour=23, minute=59, second=59, microsecond=0
                )
            elif keyword == "오늘":
                date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
                date_to = now.replace(hour=23, minute=59, second=59, microsecond=0)
            elif keyword in ("지난주", "저번주"):
                # 지난주 월요일 ~ 일요일
                days_since_monday = now.weekday()
                last_monday = now - timedelta(days=days_since_monday + 7)
                last_sunday = last_monday + timedelta(days=6)
                date_from = last_monday.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                date_to = last_sunday.replace(
                    hour=23, minute=59, second=59, microsecond=0
                )
            elif keyword in ("지난달", "저번달"):
                first_of_this_month = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                date_to = first_of_this_month - timedelta(seconds=1)
                date_from = date_to.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
            elif keyword == "최근":
                date_from = (now - timedelta(days=3)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                date_to = now
            elif keyword in (
                "이전에",
                "과거에",
                "예전에",
                "저번에",
                "지난번",
                "며칠 전",
            ):
                date_from = (now - timedelta(days=30)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                date_to = now
            break

    if not date_from:
        return None

    # 시간 키워드를 제외한 검색 키워드 추출
    keywords = _extract_search_keywords(text, matched_keyword)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "keywords": keywords,
        "time_keyword": matched_keyword,
    }


def _extract_search_keywords(
    text: str, time_keyword: Optional[str] = None
) -> List[str]:
    """시간 키워드를 제외한 검색 키워드를 추출합니다.

    Args:
        text: 원본 텍스트
        time_keyword: 감지된 시간 키워드

    Returns:
        검색용 키워드 리스트 (최대 3개)
    """
    # 2글자 이상의 한글 단어 추출
    words = re.findall(r"[가-힣]{2,}", text)

    keywords = []
    seen = set()
    for word in words:
        if word in TIME_STOPWORDS:
            continue
        if word not in seen:
            keywords.append(word)
            seen.add(word)
            if len(keywords) >= 3:
                break

    return keywords


def build_past_context_by_date(
    date_from: datetime,
    date_to: datetime,
    keywords: Optional[List[str]] = None,
    max_conversations: int = 3,
    messages_per_conv: int = 10,
) -> str:
    """날짜 범위로 과거 대화를 검색하여 포맷된 컨텍스트를 반환합니다.

    Args:
        date_from: 검색 시작 날짜
        date_to: 검색 종료 날짜
        keywords: 추가 검색 키워드 (선택적)
        max_conversations: 최대 대화 수
        messages_per_conv: 대화당 최대 메시지 수

    Returns:
        포맷된 과거 대화 컨텍스트 (빈 문자열 가능)
    """
    db = SessionLocal()
    try:
        # 날짜 범위로 대화 검색
        query = (
            db.query(Conversation)
            .filter(Conversation.started_at.between(date_from, date_to))
            .order_by(Conversation.started_at.desc())
        )

        conversations = query.limit(max_conversations).all()

        if not conversations:
            return ""

        # 키워드 필터링 (있는 경우)
        if keywords:
            filtered = []
            for conv in conversations:
                # 대화 제목 또는 메시지 내용에 키워드가 포함되어 있는지 확인
                has_keyword = False
                if conv.title:
                    for kw in keywords:
                        if kw.lower() in (conv.title or "").lower():
                            has_keyword = True
                            break

                if not has_keyword:
                    # 메시지 내용에서 검색
                    for kw in keywords:
                        msg_match = (
                            db.query(Message)
                            .filter(
                                Message.conversation_id == conv.id,
                                Message.content.ilike(f"%{kw}%"),
                            )
                            .first()
                        )
                        if msg_match:
                            has_keyword = True
                            break

                if has_keyword:
                    filtered.append(conv)

            # 키워드 매치가 없으면 날짜 범위 결과를 그대로 사용
            # (사용자가 "어제 대화"라고 했을 때 키워드가 "대화"뿐이면 필터링하지 않음)
            if filtered:
                conversations = filtered[:max_conversations]

        # 컨텍스트 포맷팅
        agent_cache: Dict[str, str] = {}
        parts = []

        for conv in conversations:
            header = f"📅 {conv.started_at.strftime('%Y-%m-%d %H:%M') if conv.started_at else '날짜 unknown'}"
            if conv.title:
                header += f" | 제목: {conv.title}"
            if conv.reference_code:
                header += f" ({conv.reference_code})"

            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
                .limit(messages_per_conv)
                .all()
            )

            msg_lines = []
            for msg in messages:
                if msg.sender_type == "user":
                    msg_lines.append(f"  👤 사용자: {_truncate(msg.content, 200)}")
                elif msg.sender_type == "agent":
                    agent_display = _get_agent_display(db, agent_cache, msg.agent_id)
                    msg_lines.append(
                        f"  🤖 {agent_display}: {_truncate(msg.content, 200)}"
                    )

            parts.append(header + "\n" + "\n".join(msg_lines))

        return "\n\n".join(parts)

    except Exception as e:
        logger.error(f"[SharedContext] build_past_context_by_date error: {e}")
        return ""
    finally:
        db.close()
