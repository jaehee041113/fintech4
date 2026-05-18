"""
crawler/run_crawler.py — 크롤링 실행 진입점
=============================================
신용카드 + 체크카드 전체 크롤링 후 MySQL DB에 저장합니다.

전체 실행 순서:
  1. crawl_card_list()  : 카드 목록 수집 (Selenium — 신용/체크 각각)
  2. crawl_card_detail(): 카드별 상세 정보 수집 (requests + BeautifulSoup)
  3. DataFrame 생성      : 수집 결과를 pandas DataFrame으로 변환
  4. DB 저장             : MySQL의 cards / card_benefits 테이블에 전체 교체 저장

이 파일은 두 가지 방식으로 호출됩니다:
  - 수동 실행  : POST /api/crawl/trigger API 호출 시 (main.py)
  - 자동 실행  : APScheduler가 매주 월요일 00:00 KST에 호출 (crawl_scheduler.py)
"""

import sys
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# 이 파일이 직접 실행될 때 backend/ 폴더를 Python 경로에 추가
# → "from dbio import ..." 같은 import가 정상 동작하도록
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler.card_list import crawl_card_list
from crawler.card_detail import crawl_card_detail
from dbio import to_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# DB 및 테이블 이름 상수
DB_NAME       = "kb_cards"
CARDS_TABLE   = "cards"         # 카드 기본 정보 테이블
BENEFITS_TABLE = "card_benefits" # 카드 혜택 정보 테이블


def run_full_crawl():
    """
    신용카드 + 체크카드 전체 크롤링 후 DB 저장

    반환값:
        저장된 카드 수 (int)

    실행 순서:
      for card_type in ["credit", "debit"]:
        1. crawl_card_list()   → 카드 목록 수집 (이름, 이미지, cooperation_code 등)
        2. crawl_card_detail() → 각 카드의 연회비, 전월실적, 혜택 상세 수집
        3. cards_rows에 카드 기본 정보 추가
        4. benefits_rows에 카드 혜택 정보 추가
      5. DataFrame 변환 후 MySQL에 저장 (기존 데이터 전체 교체)
    """
    logger.info("===== KB국민카드 크롤링 시작 =====")

    cards_rows = []    # cards 테이블에 저장할 행 목록
    benefits_rows = [] # card_benefits 테이블에 저장할 행 목록
    crawled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 크롤링 시각

    # 신용카드(credit), 체크카드(debit) 순서로 처리
    for card_type in ["credit", "debit"]:
        logger.info(f"[{card_type}] 목록 크롤링 시작")

        # ── 1단계: 카드 목록 수집 ─────────────────────────────
        # Selenium으로 KB카드 사이트의 모든 혜택 탭을 순회하며
        # 카드명, 이미지 URL, cooperation_code 등을 수집
        card_list = crawl_card_list(card_type)
        logger.info(f"[{card_type}] {len(card_list)}개 카드 목록 수집")

        # ── 2단계: 카드별 상세 정보 수집 ─────────────────────
        for card_info in card_list:
            cooperation_code = card_info.get("cooperation_code", "")
            if not cooperation_code:
                # cooperation_code가 없으면 상세 페이지 접근 불가 → 건너뜀
                logger.warning(f"cooperation_code 없음, 건너뜀: {card_info.get('name')}")
                continue

            # requests + BeautifulSoup으로 카드 상세 페이지에서
            # 연회비, 전월실적 구간, 카테고리별 혜택률 수집
            detail = crawl_card_detail(cooperation_code)

            # ── 3단계: cards 테이블 행 구성 ──────────────────
            # 이미지 URL은 cooperation_code 기반 고정 패턴으로 생성
            # (크롤링 결과와 무관하게 일관된 URL 사용)
            card_row = {
                "cooperation_code":   cooperation_code,
                "name":               card_info["name"],
                "card_type":          card_type,
                "description":        card_info.get("description", ""),
                "detail_url":         card_info.get("detail_url", ""),
                # 이미지 URL: KB카드 상품 이미지 고정 패턴 사용
                "image_url": (
                    f"https://img1.kbcard.com/ST/img/cxc/kbcard/upload/img/product/{cooperation_code}_img.png"
                ),
                "annual_fee_domestic":  None,  # 상세 크롤링 후 채워짐
                "annual_fee_overseas":  None,
                "min_spending_1":       None,  # 전월실적 1구간 기준금액
                "min_spending_2":       None,  # 전월실적 2구간 기준금액
                "min_spending_3":       None,  # 전월실적 3구간 기준금액
                "crawled_at":           crawled_at,
            }

            if detail:
                # 상세 크롤링 성공 시 → 연회비, 전월실적 데이터로 업데이트
                card_row["annual_fee_domestic"] = detail.get("annual_fee_domestic")
                card_row["annual_fee_overseas"] = detail.get("annual_fee_overseas")
                card_row["min_spending_1"]      = detail.get("min_spending_1")
                card_row["min_spending_2"]      = detail.get("min_spending_2")
                card_row["min_spending_3"]      = detail.get("min_spending_3")

                # ── 4단계: card_benefits 테이블 행 구성 ──────
                # 카드 1개당 여러 혜택 행이 생성됨
                # (예: 음식/카페 할인, 주유/교통 적립, 쇼핑 할인 등)
                for benefit in detail.get("benefits", []):
                    benefits_rows.append({
                        "cooperation_code": cooperation_code,
                        "category":         benefit["category"],      # 혜택 카테고리
                        "benefit_type":     benefit["benefit_type"],  # 할인/적립 유형
                        "rate_min":         benefit.get("rate_min"),  # 혜택률 최솟값 (%)
                        "rate_max":         benefit.get("rate_max"),  # 혜택률 최댓값 (%)
                        "max_amount_1":     benefit.get("max_amount_1"),  # 1구간 월 최대 혜택
                        "max_amount_2":     benefit.get("max_amount_2"),  # 2구간 월 최대 혜택
                        "max_amount_3":     benefit.get("max_amount_3"),  # 3구간 월 최대 혜택
                        "conditions":       benefit.get("conditions", ""),
                        "description":      benefit.get("description", ""),
                    })
            else:
                # image_url은 이미 위에서 설정됨 (상세 크롤링 실패해도 이미지 URL은 유지)
                pass

            cards_rows.append(card_row)
            logger.info(f"[{card_info['name']}] 수집 완료")

    if not cards_rows:
        logger.warning("수집된 카드가 없습니다.")
        return 0

    # ── 5단계: DataFrame 생성 ─────────────────────────────────
    # 리스트(dict)를 pandas DataFrame으로 변환
    cards_df    = pd.DataFrame(cards_rows)
    benefits_df = pd.DataFrame(benefits_rows) if benefits_rows else pd.DataFrame()

    # ── 6단계: DB 저장 (전체 교체 방식) ─────────────────────
    # replace=True: 기존 테이블 삭제 후 새 데이터로 완전 교체
    # → 크롤링할 때마다 항상 최신 데이터만 유지
    _save_to_db(DB_NAME, CARDS_TABLE, cards_df, replace=True)
    if not benefits_df.empty:
        _save_to_db(DB_NAME, BENEFITS_TABLE, benefits_df, replace=True)

    total = len(cards_df)
    logger.info(f"===== 크롤링 완료: 카드 {total}개, 혜택 {len(benefits_df)}개 저장 =====")
    return total


def _save_to_db(dbname: str, table_name: str, df: pd.DataFrame, replace: bool = False):
    """
    DataFrame을 MySQL에 저장합니다.

    Args:
        dbname     : 데이터베이스 이름
        table_name : 저장할 테이블 이름
        df         : 저장할 DataFrame
        replace    : True면 기존 테이블 전체 교체, False면 추가(append)

    replace=True 동작 방식:
      - SQLAlchemy engine을 직접 생성해 DataFrame.to_sql(if_exists="replace") 사용
      - dbio.to_db()는 append 전용이므로, replace가 필요할 때는 이 함수에서 직접 처리
    """
    if replace:
        # replace 모드: 기존 테이블을 삭제하고 새로 생성
        import os
        from sqlalchemy import create_engine, text
        import pymysql
        pymysql.install_as_MySQLdb()
        from dotenv import load_dotenv
        load_dotenv()

        dbid = os.getenv("dbid")
        dbpw = os.getenv("dbpw")
        host = os.getenv("host")
        port = os.getenv("port")

        # DB가 없으면 먼저 생성
        engine_root = create_engine(f"mysql+pymysql://{dbid}:{dbpw}@{host}:{port}")
        with engine_root.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {dbname}"))
            conn.commit()

        # 테이블에 데이터 저장 (if_exists="replace": 기존 테이블 삭제 후 재생성)
        engine = create_engine(f"mysql+pymysql://{dbid}:{dbpw}@{host}:{port}/{dbname}")
        df.to_sql(table_name, con=engine, index=False, if_exists="replace")
        logger.info(f"{dbname}.{table_name} 데이터 저장 완료 (replace, {len(df)}행)")
    else:
        # append 모드: dbio.to_db() 사용
        to_db(dbname, table_name, df)


# 이 파일을 직접 실행할 때 (python run_crawler.py)
if __name__ == "__main__":
    run_full_crawl()
