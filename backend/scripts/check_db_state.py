#!/usr/bin/env python3
"""
DB 상태 검증 스크립트

한 번에 아래 정보를 확인할 수 있습니다:
  1. 현재 DATABASE_URL
  2. 실제 SQLite 파일 절대 경로
  3. agents 수 및 role별 목록
  4. conversations 수
  5. messages 수
  6. Claw(openclaw-bot) 존재 여부
  7. 루트 DB / 백엔드 DB 중복 존재 여부

사용법:
    python -m backend.scripts.check_db_state
    python backend/scripts/check_db_state.py
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database import SessionLocal
from models.agent import Agent


def check_db_state():
    """Check and print database state."""
    # ── 1. DATABASE_URL ──
    db_url = settings.database_url
    db_path_str = db_url.replace("sqlite:///", "")
    db_path = Path(db_path_str)

    print("=" * 65)
    print("  AI Virtual Company — DB 상태 검증")
    print("=" * 65)

    print(f"\n  ▶ DB 설정")
    print(f"    DATABASE_URL: {db_url}")
    print(f"    실제 파일 경로: {db_path.resolve()}")
    print(f"    파일 존재: {'✅' if db_path.exists() else '❌'} (size: {db_path.stat().st_size / 1024:.1f} KB)" if db_path.exists() else f"    파일 존재: ❌")

    # ── 2. 루트 DB 중복 검사 ──
    backend_dir = Path(__file__).resolve().parent.parent  # backend/
    project_root = backend_dir.parent  # my-ai-company/
    root_db = project_root / "ai_company.db"
    backend_db = backend_dir / "ai_company.db"

    print(f"\n  ▶ DB 중복 검사")
    root_exists = root_db.exists()
    backend_exists = backend_db.exists()
    same_file = db_path.resolve() == backend_db.resolve()

    if root_exists:
        root_size = root_db.stat().st_size / 1024
        print(f"    ⚠️  루트 DB 발견: {root_db} ({root_size:.1f} KB)")
    else:
        print(f"    ✅ 루트 DB 없음 (정상)")

    if backend_exists:
        backend_size = backend_db.stat().st_size / 1024
        print(f"    백엔드 DB: {backend_db} ({backend_size:.1f} KB)")
    else:
        print(f"    ❌ 백엔드 DB 없음!")

    if root_exists and backend_exists:
        print(f"    ⚠️  경고: DB 파일이 2개 존재합니다!")
        print(f"    현재 설정이 가리키는 쪽: {'✅ backend DB' if same_file else '❌ 루트 DB (잘못된 설정!)'}")
    elif root_exists:
        print(f"    ⚠️  현재 설정의 DB 파일이 backend/ 위치가 아닙니다")
    else:
        print(f"    ✅ DB 파일 상태 정상")

    # ── 3. DB 연결 및 데이터 확인 ──
    print(f"\n  ▶ DB 연결")
    try:
        db = SessionLocal()
        print(f"    ✅ DB 연결 성공")
    except Exception as e:
        print(f"    ❌ DB 연결 실패: {e}")
        return

    try:
        # Agents
        agents_count = db.query(Agent).count()
        agents_list = db.query(Agent).all()
        print(f"\n  ▶ Agents: {agents_count}명")
        for a in agents_list:
            flag = " ✅ (Claw)" if a.id == "openclaw-bot" else ""
            print(f"    - [{a.role}] {a.name} ({a.display_name or a.name}){flag}")

        # Conversations
        from models.conversation import Conversation
        conv_count = db.query(Conversation).count()
        print(f"\n  ▶ Conversations: {conv_count}개")

        # Messages
        from models.message import Message
        msg_count = db.query(Message).count()
        print(f"  ▶ Messages: {msg_count}개")

        # Claw 확인
        claw = db.query(Agent).filter(Agent.id == "openclaw-bot").first()
        if claw:
            print(f"\n  ▶ Claw(openclaw-bot): ✅ 존재 (name={claw.name}, role={claw.role})")
        else:
            # role=bot 으로 다시 확인
            claw_by_role = db.query(Agent).filter(Agent.role == "bot").first()
            if claw_by_role:
                print(f"\n  ▶ Claw(role=bot): ⚠️ id가 openclaw-bot이 아님 (id={claw_by_role.id}, name={claw_by_role.name})")
            else:
                print(f"\n  ▶ Claw: ❌ 존재하지 않음")

    except Exception as e:
        print(f"\n  ▶ 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print("\n" + "=" * 65)
    print("  검증 완료")
    print("=" * 65)


if __name__ == "__main__":
    check_db_state()
