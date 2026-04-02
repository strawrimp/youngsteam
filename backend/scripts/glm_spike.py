"""
GLM Multi-Agent CLI Spike Test

This script tests the core assumption: can GLM handle multi-agent conversations
where agents exchange opinions synchronously and reach consensus through voting?

Run this before Phase 2 to validate:
1. GLM API connectivity
2. Multi-agent prompt structure
3. Voting/consensus logic
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

from services.glm_service import GLMService
from collections import Counter
import json

# Agent definitions
AGENTS = {
    "manager": {
        "name": "Manager (CEO)",
        "prompt": "당신은 회사의 CEO입니다. 전략적 관점에서 의견을 제시하세요.",
    },
    "developer": {
        "name": "Developer",
        "prompt": "당신은 기술 리드입니다. 기술적 가능성과 복잡도를 고려하여 의견을 제시하세요.",
    },
    "designer": {
        "name": "Designer",
        "prompt": "당신은 디자인 리드입니다. 사용자 경험 관점에서 의견을 제시하세요.",
    },
    "researcher": {
        "name": "Researcher",
        "prompt": "당신은 리서처입니다. 데이터와 분석 기반 의견을 제시하세요.",
    },
}


async def get_agent_opinion(glm: GLMService, agent_key: str, topic: str) -> str:
    """Get an agent's opinion on a topic."""
    agent = AGENTS[agent_key]
    prompt = f"""{agent['prompt']}

주제: {topic}

당신의 의견을 명확하고 간결하게 제시하세요. (2-3문장)"""

    response = await glm.call_model(
        system_prompt=agent["prompt"],
        user_message=prompt,
    )
    return response


async def get_agent_vote(glm: GLMService, agent_key: str, topic: str, candidates: list) -> str:
    """Get an agent's vote on candidates."""
    agent = AGENTS[agent_key]
    candidates_str = "\n".join([f"{i+1}. {c}" for i, c in enumerate(candidates)])

    prompt = f"""{agent['prompt']}

주제: {topic}

선택지:
{candidates_str}

위 선택지 중 하나를 선택하고, 선택한 이유를 간단히 설명하세요.
형식: "선택: [선택 번호]"로 시작하세요."""

    response = await glm.call_model(
        system_prompt=agent["prompt"],
        user_message=prompt,
    )
    return response


def extract_choice(response: str, candidates: list) -> str:
    """Extract choice from agent response."""
    # Try to find "선택: [number]" pattern
    lines = response.split("\n")
    for line in lines:
        if "선택:" in line:
            # Extract the number
            for i, candidate in enumerate(candidates, 1):
                if str(i) in line:
                    return candidate
    # Fallback: return first candidate
    return candidates[0]


async def run_spike_test():
    """Run the GLM multi-agent spike test."""
    print("=" * 60)
    print("GLM Multi-Agent Spike Test")
    print("=" * 60)

    glm = GLMService()

    # Test 1: Opinion gathering
    print("\n[Test 1] 의견 수집")
    print("-" * 60)
    topic = "새로운 AI 기능으로 이미지 생성 능력을 추가해야 할까?"
    print(f"주제: {topic}\n")

    opinions = {}
    for agent_key in AGENTS.keys():
        agent_name = AGENTS[agent_key]["name"]
        print(f"{agent_name}의 의견을 수집 중...")

        try:
            opinion = await get_agent_opinion(glm, agent_key, topic)
            opinions[agent_key] = opinion
            print(f"✓ {agent_name}: {opinion[:80]}...\n")
        except Exception as e:
            print(f"✗ {agent_name} 오류: {e}\n")

    # Test 2: Voting and consensus
    print("\n[Test 2] 투표 및 의견 수렴")
    print("-" * 60)
    voting_topic = "이미지 생성 기능"
    candidates = ["지금 구현", "다음 분기에 구현", "외부 API 통합 검토"]

    print(f"주제: {voting_topic}")
    print(f"선택지: {candidates}\n")

    votes = {}
    for agent_key in AGENTS.keys():
        agent_name = AGENTS[agent_key]["name"]
        print(f"{agent_name}의 투표를 수집 중...")

        try:
            vote_response = await get_agent_vote(glm, agent_key, voting_topic, candidates)
            choice = extract_choice(vote_response, candidates)
            votes[agent_key] = choice
            print(f"✓ {agent_name}: {choice}\n")
        except Exception as e:
            print(f"✗ {agent_key} 오류: {e}\n")

    # Calculate consensus
    print("\n[Test 3] 컨센서스 계산")
    print("-" * 60)

    if votes:
        vote_counts = Counter(votes.values())
        winning_vote, vote_count = vote_counts.most_common(1)[0]

        print(f"투표 결과:")
        for agent_key, choice in votes.items():
            print(f"  {AGENTS[agent_key]['name']}: {choice}")

        print(f"\n투표 집계:")
        for choice, count in vote_counts.most_common():
            print(f"  {choice}: {count}표")

        print(f"\n최종 결정: {winning_vote} ({vote_count}/{len(votes)})")

        # Check for tie
        if len(vote_counts) > 1 and vote_counts[0][1] == vote_counts[1][1]:
            print("⚠️  동점 발생 - 관리자의 최종 판단 필요")

    print("\n" + "=" * 60)
    print("✓ 스파이크 테스트 완료")
    print("=" * 60)


async def main():
    """Main entry point."""
    try:
        await run_spike_test()
    except KeyboardInterrupt:
        print("\n\n✗ 테스트 중단됨")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
