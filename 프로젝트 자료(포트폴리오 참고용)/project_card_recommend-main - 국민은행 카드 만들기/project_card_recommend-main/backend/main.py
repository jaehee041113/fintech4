"""
main.py — FastAPI 메인 애플리케이션
=====================================
이 파일이 백엔드 서버의 시작점입니다.
Docker Compose가 "uvicorn main:app ..." 명령으로 이 파일을 실행합니다.

제공하는 API:
  GET  /api/cards              → 카드 목록 조회
  GET  /api/cards/{code}       → 카드 상세 조회
  GET  /api/categories         → 혜택 카테고리 목록
  POST /api/recommend          → 지출 패턴 기반 카드 추천
  POST /api/crawl/trigger      → 크롤링 수동 실행
  GET  /api/crawl/schedule     → 스케줄러 상태 조회
  GET  /health                 → 헬스체크

서버 시작 시 자동으로 APScheduler가 활성화되어
매주 월요일 00:00 KST에 크롤링이 자동 실행됩니다.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from dbio import from_db
from recommend import recommend_cards_ml, BENEFIT_CATEGORIES
from scheduler.crawl_scheduler import create_scheduler

# 로그 포맷 설정: "2026-04-08 12:00:00 [INFO] recommend - 메시지" 형태로 출력
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_NAME   = "kb_cards"  # MySQL 데이터베이스 이름
scheduler = create_scheduler()  # 자동 크롤링 스케줄러 생성 (아직 시작 안 됨)


# ── 서버 시작/종료 이벤트 처리 ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 서버의 생명주기를 관리합니다.

    - yield 이전: 서버 시작 시 실행 (스케줄러 시작)
    - yield 이후: 서버 종료 시 실행 (스케줄러 정지)

    이 방식은 FastAPI의 권장 방식으로, 기존 @app.on_event("startup")을 대체합니다.
    """
    # 서버 시작: 백그라운드 스케줄러 시작
    scheduler.start()
    logger.info("FastAPI 서버 시작 - 스케줄러 활성화 (매주 월요일 00:00 KST)")
    yield
    # 서버 종료: 스케줄러 정리
    scheduler.shutdown()
    logger.info("FastAPI 서버 종료 - 스케줄러 비활성화")


# ── FastAPI 앱 생성 ────────────────────────────────────────
app = FastAPI(
    title="KB국민카드 추천 API",
    description="카드 정보 크롤링 및 사용자 지출 패턴 기반 카드 추천 서비스",
    version="1.0.0",
    lifespan=lifespan,  # 위에서 정의한 생명주기 함수 등록
)

# ── CORS 설정 ─────────────────────────────────────────────
# CORS(Cross-Origin Resource Sharing): 다른 도메인에서의 API 접근 허용 설정
# 프론트엔드(localhost:3000)에서 백엔드(localhost:8000)로 요청할 수 있도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 허용할 출처 (로컬 개발용)
    allow_credentials=True,
    allow_methods=["*"],   # 모든 HTTP 메서드 허용 (GET, POST 등)
    allow_headers=["*"],   # 모든 헤더 허용
)


# ── Pydantic 입력 스키마 정의 ──────────────────────────────
# Pydantic: FastAPI에서 요청 데이터의 타입과 유효성을 자동으로 검사하는 라이브러리

class SpendingInput(BaseModel):
    """
    카테고리별 월 지출 금액 입력 모델

    "음식/카페" 같이 슬래시(/)가 포함된 필드명은 Python 변수명으로 사용 불가.
    → alias를 사용해 JSON 키 이름(alias)과 Python 변수명을 분리합니다.
      예) JSON: {"음식/카페": 200000} → Python: self.음식_카페 = 200000
    """
    전가맹점:    int = Field(default=0, ge=0)  # ge=0: 0 이상만 허용
    음식_카페:   int = Field(default=0, ge=0, alias="음식/카페")
    주유_교통:   int = Field(default=0, ge=0, alias="주유/교통")
    쇼핑_간편결제: int = Field(default=0, ge=0, alias="쇼핑/간편결제")
    항공_해외:   int = Field(default=0, ge=0, alias="항공/해외")
    교육_건강:   int = Field(default=0, ge=0, alias="교육/건강")
    자동납부:    int = Field(default=0, ge=0)
    통신:       int = Field(default=0, ge=0)
    Biz_공공:   int = Field(default=0, ge=0, alias="Biz/공공")

    # populate_by_name=True: alias 없이 Python 변수명으로도 값을 채울 수 있게 허용
    model_config = {"populate_by_name": True}

    def to_category_dict(self) -> dict[str, int]:
        """
        내부 Python 변수명 → 원래 카테고리 이름으로 변환합니다.
        recommend.py에서 카테고리명으로 혜택을 찾을 때 사용합니다.
        """
        return {
            "전가맹점":     self.전가맹점,
            "음식/카페":    self.음식_카페,
            "주유/교통":    self.주유_교통,
            "쇼핑/간편결제": self.쇼핑_간편결제,
            "항공/해외":    self.항공_해외,
            "교육/건강":    self.교육_건강,
            "자동납부":     self.자동납부,
            "통신":        self.통신,
            "Biz/공공":    self.Biz_공공,
        }


class RecommendRequest(BaseModel):
    """
    카드 추천 API 요청 모델

    요청 예시 (JSON):
    {
        "spending": {"음식/카페": 300000, "주유/교통": 150000},
        "card_type": "credit",
        "top_n": 5
    }
    """
    spending:  SpendingInput           # 카테고리별 월 지출 금액
    card_type: Optional[str] = Field(default=None, description="credit | debit | null(전체)")
    top_n:     int           = Field(default=5, ge=1, le=20)  # 추천 카드 수 (1~20)


# ── 카드 목록/상세 API ─────────────────────────────────────

@app.get("/api/cards", summary="카드 목록 조회")
def get_cards(card_type: Optional[str] = Query(None, description="credit | debit")):
    """
    DB에서 카드 목록을 조회합니다.

    Query 파라미터:
        card_type: "credit"(신용) | "debit"(체크) | 생략(전체)

    예시: GET /api/cards?card_type=credit
    """
    try:
        df = from_db(DB_NAME, "cards")
    except Exception:
        raise HTTPException(status_code=503, detail="DB 연결 실패. 크롤링을 먼저 실행하세요.")

    # card_type 필터 적용
    if card_type in ("credit", "debit"):
        df = df[df["card_type"] == card_type]

    # NaN 값을 None으로 변환 (JSON 직렬화 시 NaN 오류 방지)
    cards = df.where(df.notna(), None).to_dict(orient="records")
    return {"cards": cards, "total": len(cards)}


@app.get("/api/cards/{cooperation_code}", summary="카드 상세 조회")
def get_card_detail(cooperation_code: str):
    """
    특정 카드의 상세 정보와 혜택 목록을 조회합니다.

    Path 파라미터:
        cooperation_code: 카드 고유 코드 (예: "09060")

    예시: GET /api/cards/09060
    """
    try:
        cards_df    = from_db(DB_NAME, "cards")
        benefits_df = from_db(DB_NAME, "card_benefits")
    except Exception:
        raise HTTPException(status_code=503, detail="DB 연결 실패.")

    # cooperation_code로 카드 검색
    card_rows = cards_df[cards_df["cooperation_code"] == cooperation_code]
    if card_rows.empty:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없습니다.")

    # 첫 번째 행(유일한 카드)을 dict로 변환
    card = card_rows.iloc[0].where(card_rows.iloc[0].notna(), None).to_dict()

    # 해당 카드의 혜택 목록 추가
    benefits = benefits_df[benefits_df["cooperation_code"] == cooperation_code]
    card["benefits"] = benefits.where(benefits.notna(), None).to_dict(orient="records")

    return card


@app.get("/api/categories", summary="혜택 카테고리 목록")
def get_categories():
    """지원하는 혜택 카테고리 목록을 반환합니다."""
    return {"categories": BENEFIT_CATEGORIES}


# ── 추천 API ──────────────────────────────────────────────

@app.post("/api/recommend", summary="카드 추천")
def recommend(request: RecommendRequest):
    """
    사용자의 카테고리별 월 지출 금액을 받아 최적 카드를 추천합니다.

    처리 순서:
      1. 요청 데이터 유효성 검사 (Pydantic이 자동 처리)
      2. SpendingInput을 카테고리 dict로 변환
      3. recommend_cards_ml() 호출 → 혜택 계산 + 순위 결정
      4. 결과 반환

    요청 예시 (JSON Body):
    {
        "spending": {"음식/카페": 300000, "주유/교통": 150000},
        "card_type": "credit",
        "top_n": 5
    }
    """
    spending = request.spending.to_category_dict()

    # 모든 카테고리 지출이 0이면 추천 불가
    if sum(spending.values()) == 0:
        raise HTTPException(status_code=400, detail="최소 하나의 카테고리에 지출 금액을 입력하세요.")

    results = recommend_cards_ml(
        spending=spending,
        card_type=request.card_type,
        top_n=request.top_n,
    )
    return {
        "input_spending":          spending,
        "total_monthly_spending":  sum(spending.values()),
        "recommendations":         results,
    }


# ── 크롤링 API ────────────────────────────────────────────

@app.post("/api/crawl/trigger", summary="크롤링 수동 실행")
def trigger_crawl(background_tasks: BackgroundTasks):
    """
    크롤링을 백그라운드에서 즉시 실행합니다.

    - BackgroundTasks: FastAPI 기능으로, API 응답을 먼저 반환한 뒤
      백그라운드에서 함수를 실행합니다.
    - 크롤링은 수분 소요되므로, 응답 대기 없이 즉시 "시작됨" 메시지를 반환합니다.

    진행 상황 확인: docker logs -f kb_backend
    """
    def run():
        # import를 함수 내부에서 수행 (순환 참조 방지)
        from crawler.run_crawler import run_full_crawl
        run_full_crawl()

    background_tasks.add_task(run)
    return {"message": "크롤링이 백그라운드에서 시작되었습니다."}


@app.get("/api/crawl/schedule", summary="스케줄러 상태 조회")
def get_schedule_info():
    """
    현재 등록된 스케줄 작업 목록과 다음 실행 시각을 반환합니다.
    """
    jobs = [
        {
            "id":       job.id,
            "name":     job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        }
        for job in scheduler.get_jobs()
    ]
    return {"scheduler_running": scheduler.running, "jobs": jobs}


# ── 헬스체크 ──────────────────────────────────────────────

@app.get("/health")
def health():
    """
    서버 정상 동작 여부를 확인합니다.
    nginx나 모니터링 도구에서 주기적으로 호출해 서버 상태를 체크합니다.
    """
    return {"status": "ok"}
