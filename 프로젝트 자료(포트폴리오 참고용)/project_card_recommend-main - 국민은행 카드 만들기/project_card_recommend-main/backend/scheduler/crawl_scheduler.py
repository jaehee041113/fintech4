"""
scheduler/crawl_scheduler.py — 자동 크롤링 스케줄러
=====================================================
APScheduler를 사용해 매주 월요일 00:00 KST에 크롤링을 자동 실행합니다.

실행 흐름:
  1. FastAPI 서버 시작 시 create_scheduler() 호출 (main.py의 lifespan 참고)
  2. BackgroundScheduler가 별도 스레드에서 대기
  3. 매주 월요일 자정이 되면 _crawl_job() 실행
  4. _crawl_job()이 run_full_crawl()을 호출해 크롤링 시작
  5. 완료/실패 여부를 _job_listener()가 로그에 기록

스케줄러는 서버가 실행 중인 동안 계속 백그라운드에서 동작합니다.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import pytz

logger = logging.getLogger(__name__)

# 한국 표준시(KST) 타임존 객체
KST = pytz.timezone("Asia/Seoul")


def _crawl_job():
    """
    스케줄러가 실행하는 크롤링 작업 함수

    - import를 함수 내부에서 수행하는 이유:
      서버 시작 시점에는 DB가 아직 준비되지 않을 수 있으므로,
      실제 실행 시점에 import해 최신 상태로 동작하도록 합니다.
    """
    # 실행 시점에 import (순환 참조 및 초기화 타이밍 문제 방지)
    from crawler.run_crawler import run_full_crawl

    logger.info("[Scheduler] 주간 크롤링 작업 시작")
    try:
        count = run_full_crawl()
        logger.info(f"[Scheduler] 주간 크롤링 완료: {count}개 카드 처리")
    except Exception as e:
        logger.error(f"[Scheduler] 크롤링 오류: {e}")


def _job_listener(event):
    """
    스케줄러 작업 완료/실패 이벤트 리스너

    APScheduler는 작업이 끝나면 이 함수를 자동으로 호출합니다.
    event.exception이 있으면 실패, 없으면 성공입니다.
    """
    if event.exception:
        logger.error(f"[Scheduler] 작업 실패: {event.job_id} - {event.exception}")
    else:
        logger.info(f"[Scheduler] 작업 성공: {event.job_id}")


def create_scheduler() -> BackgroundScheduler:
    """
    APScheduler BackgroundScheduler를 생성하고 반환합니다.

    - BackgroundScheduler: 메인 스레드를 차단하지 않고 백그라운드에서 실행
    - CronTrigger: cron 표현식으로 실행 시각 지정
      (day_of_week="mon", hour=0, minute=0 → 매주 월요일 00:00)

    Returns:
        설정이 완료된 BackgroundScheduler (아직 시작되지 않은 상태)
        → main.py의 lifespan에서 scheduler.start()로 시작됩니다.
    """
    # KST 기준으로 스케줄러 생성
    scheduler = BackgroundScheduler(timezone=KST)

    # 크롤링 작업 등록
    scheduler.add_job(
        func=_crawl_job,                    # 실행할 함수
        trigger=CronTrigger(
            day_of_week="mon",              # 월요일
            hour=0,                         # 0시
            minute=0,                       # 0분
            second=0,
            timezone=KST,
        ),
        id="weekly_card_crawl",             # 작업 고유 ID
        name="매주 월요일 자정 KB국민카드 크롤링",
        replace_existing=True,              # 서버 재시작 시 중복 등록 방지
        misfire_grace_time=3600,            # 서버가 꺼져 있다 켜진 경우, 1시간 이내면 재실행
    )

    # 작업 완료/실패 이벤트 리스너 등록
    # EVENT_JOB_EXECUTED: 작업 성공 이벤트
    # EVENT_JOB_ERROR: 작업 실패 이벤트
    scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    return scheduler
