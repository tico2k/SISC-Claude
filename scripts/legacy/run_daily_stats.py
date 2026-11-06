import os
import sys
from datetime import datetime

# backend 모듈을 로드하기 위해 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.tasks.batch_tasks import generate_daily_statistics

def main():
    if len(sys.argv) < 2:
        print("사용법: python run_daily_stats.py YYYY-MM-DD")
        print("설명: 입력하신 날짜(예: 2026-03-01)에 해당하는 일일 통계를 강제로 수집/갱신합니다.")
        sys.exit(1)

    target_date_str = sys.argv[1]
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        print("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요. (예: 2026-03-01)")
        sys.exit(1)

    print(f"🚀 {target_date} 일자에 대한 통계 수집 배치를 시작합니다...")
    try:
        stats = generate_daily_statistics(target_date=target_date)
        print(f"✅ 실행 완료: {stats}")
    except Exception as e:
        print(f"❌ 실행 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
