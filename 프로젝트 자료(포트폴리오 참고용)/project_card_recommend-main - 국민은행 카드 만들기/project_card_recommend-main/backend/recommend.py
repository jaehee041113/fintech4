"""
recommend.py — 카드 추천 엔진
================================
사용자가 입력한 카테고리별 월 지출 금액을 기반으로
각 카드의 예상 혜택 금액을 계산하고 순위를 매겨 추천합니다.

추천 계산 순서:
  1. MySQL에서 cards + card_benefits 데이터 로드
  2. 카드별로 _calc_card_score() 호출
     a. 총 지출액 기준 전월실적 구간 판정 (1~3구간, 0=미달)
     b. 카테고리별 혜택률(rate_min) × 지출액 = 예상 혜택
     c. 구간별 월 최대 혜택(max_amount_N) 한도 적용
     d. 해당 카테고리 혜택 없으면 '전가맹점' 혜택으로 대체
  3. 연 순 혜택(= 월 혜택 × 12 − 연회비) 기준 내림차순 정렬
  4. 상위 top_n개 반환

TODO: recommend_cards_ml()에 Jupyter notebook ML 로직 이식 예정
"""

import logging
import pandas as pd
from dbio import from_db

logger = logging.getLogger(__name__)

DB_NAME        = "kb_cards"
CARDS_TABLE    = "cards"
BENEFITS_TABLE = "card_benefits"

# 지원하는 혜택 카테고리 목록 (프론트엔드와 동일하게 유지)
BENEFIT_CATEGORIES = [
    "전가맹점",
    "음식/카페",
    "주유/교통",
    "쇼핑/간편결제",
    "항공/해외",
    "교육/건강",
    "자동납부",
    "통신",
    "Biz/공공",
]


def _load_data(card_type: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    MySQL에서 카드 목록과 혜택 데이터를 로드합니다.

    Args:
        card_type: "credit"(신용) | "debit"(체크) | None(전체)

    Returns:
        (cards_df, benefits_df) 튜플
        - 로드 실패 시 빈 DataFrame 반환 (크롤링이 아직 안 된 경우)
    """
    try:
        cards_df    = from_db(DB_NAME, CARDS_TABLE)
        benefits_df = from_db(DB_NAME, BENEFITS_TABLE)
    except Exception as e:
        logger.error(f"DB 로드 실패: {e}. 크롤링을 먼저 실행하세요.")
        return pd.DataFrame(), pd.DataFrame()

    # card_type 필터 적용
    if card_type in ("credit", "debit"):
        cards_df = cards_df[cards_df["card_type"] == card_type]

    return cards_df, benefits_df


def _calc_card_score(
    card: pd.Series,
    benefits: pd.DataFrame,
    spending: dict[str, int],
) -> dict:
    """
    카드 1개의 예상 혜택 금액을 계산합니다.

    Args:
        card     : cards 테이블의 1행 (카드 기본 정보)
        benefits : card_benefits 테이블 전체 (모든 카드의 혜택)
        spending : 사용자 입력 {"음식/카페": 200000, "주유/교통": 100000, ...}

    Returns:
        카드 정보 + 예상 혜택 계산 결과 dict

    계산 흐름:
      1. 전월실적 구간 판정 (spending_tier 0~3)
      2. 카테고리별 최고 혜택 선택 (rate_min 기준)
      3. 지출액 × 혜택률 = 예상 혜택, 한도 적용
      4. 연 순 혜택 계산
    """
    cooperation_code = card["cooperation_code"]

    # 이 카드에 해당하는 혜택만 필터링
    card_benefits = benefits[benefits["cooperation_code"] == cooperation_code]

    # ── 1단계: 전월실적 구간 판정 ────────────────────────────
    # 사용자의 총 지출액이 어느 구간에 해당하는지 판정
    # spending_tier: 0=미달(혜택 없음), 1=1구간, 2=2구간, 3=3구간
    total_spending = sum(spending.values())
    min_s1 = card.get("min_spending_1") or 0  # 1구간 최소 실적 (예: 30만원)
    min_s2 = card.get("min_spending_2") or 0  # 2구간 최소 실적 (예: 50만원)
    min_s3 = card.get("min_spending_3") or 0  # 3구간 최소 실적 (예: 100만원)

    if min_s1 == 0:
        # 전월실적 조건이 없는 카드 → 항상 1구간 적용
        spending_tier = 1
    elif total_spending >= (min_s3 or float("inf")):
        spending_tier = 3  # 3구간 이상 충족
    elif total_spending >= (min_s2 or float("inf")):
        spending_tier = 2  # 2구간 충족
    elif total_spending >= min_s1:
        spending_tier = 1  # 1구간 충족
    else:
        spending_tier = 0  # 최소 실적 미달 → 혜택 없음

    # ── 2단계: 카테고리별 최고 혜택 선택 ─────────────────────
    # 같은 카테고리에 여러 혜택이 있을 경우 rate_min이 가장 높은 것 선택
    # (보수적 추천: 확실한 혜택률만 계산)
    best_by_category: dict[str, pd.Series] = {}
    for _, benefit in card_benefits.iterrows():
        cat = benefit["category"]
        if cat not in best_by_category:
            best_by_category[cat] = benefit
        elif (benefit["rate_min"] or 0) > (best_by_category[cat]["rate_min"] or 0):
            best_by_category[cat] = benefit  # 더 높은 혜택률로 교체

    # ── 3단계: 카테고리별 혜택 금액 계산 ─────────────────────
    monthly_benefit = 0.0  # 이 카드의 월 총 예상 혜택
    breakdown = []         # 카테고리별 세부 혜택 내역

    for category, amount in spending.items():
        if amount <= 0:
            continue  # 지출이 0인 카테고리는 건너뜀

        if spending_tier == 0:
            continue  # 전월실적 미달 시 모든 혜택 제외

        # 직접 매칭 → 없으면 '전가맹점' 혜택으로 대체
        benefit = best_by_category.get(category)
        if benefit is None:
            # 해당 카테고리 혜택이 없으면 '전가맹점' 혜택 적용
            # (전가맹점 = 모든 가맹점 공통 적용 혜택)
            benefit = best_by_category.get("전가맹점")
        if benefit is None or not benefit["rate_min"]:
            continue  # 전가맹점 혜택도 없으면 이 카테고리는 혜택 없음

        # 예상 혜택 = 지출액 × 혜택률(%)
        benefit_amount = amount * (benefit["rate_min"] / 100)

        # 구간별 월 최대 혜택 한도 적용
        # (예: 3구간이면 max_amount_3 사용, 없으면 max_amount_1로 대체)
        max_key = f"max_amount_{spending_tier}"
        max_amount = benefit.get(max_key)
        if not max_amount:
            max_amount = benefit.get("max_amount_1")  # 상위 구간 한도 없으면 1구간 사용
        if max_amount and max_amount > 0:
            benefit_amount = min(benefit_amount, max_amount)  # 한도 초과 방지

        monthly_benefit += benefit_amount

        # 세부 내역 저장 (프론트엔드의 benefit_breakdown에 표시)
        breakdown.append({
            "category":         category,
            "spending":         amount,
            "rate_min":         benefit["rate_min"],
            "rate_max":         benefit["rate_max"],
            "benefit_type":     benefit["benefit_type"],
            "spending_tier":    spending_tier,
            "estimated_benefit": round(benefit_amount),
        })

    # ── 4단계: 연 순 혜택 계산 ───────────────────────────────
    annual_benefit = monthly_benefit * 12

    # 연회비: NaN(데이터 없음)이면 0으로 처리
    annual_fee = float(card.get("annual_fee_domestic") or 0)
    if annual_fee != annual_fee:  # NaN 확인 (NaN은 자기 자신과 같지 않음)
        annual_fee = 0.0

    # 연 순 혜택 = 연간 예상 혜택 - 연회비
    net_annual_benefit = annual_benefit - annual_fee

    def _safe_val(v):
        """
        pandas에서 읽어온 값의 NaN/None을 안전하게 처리합니다.
        - None → None
        - NaN  → None
        - 숫자  → int 변환
        JSON은 NaN을 지원하지 않으므로 반드시 변환 필요
        """
        if v is None:
            return None
        try:
            f = float(v)
            return None if f != f else int(f)  # NaN 이면 None 반환
        except (TypeError, ValueError):
            return None

    # 최종 결과 반환 (프론트엔드 CardResult 컴포넌트에서 사용)
    return {
        "card": {
            "cooperation_code":   cooperation_code,
            "name":               card["name"],
            "card_type":          card["card_type"],         # "credit" | "debit"
            "description":        card.get("description", ""),
            "image_url":          card.get("image_url", ""),
            "detail_url":         card.get("detail_url", ""), # KB카드 상세 페이지 URL
            "annual_fee_domestic": _safe_val(card.get("annual_fee_domestic")),
            "annual_fee_overseas": _safe_val(card.get("annual_fee_overseas")),
            "min_spending_1":     _safe_val(card.get("min_spending_1")),
            "min_spending_2":     _safe_val(card.get("min_spending_2")),
            "min_spending_3":     _safe_val(card.get("min_spending_3")),
            "applicable_tier":   spending_tier,  # 사용자가 해당하는 전월실적 구간
        },
        "monthly_benefit":    round(monthly_benefit),
        "annual_benefit":     round(annual_benefit),
        "net_annual_benefit": round(net_annual_benefit),
        "benefit_breakdown":  breakdown,  # 카테고리별 세부 내역
    }


def recommend_cards(
    spending: dict[str, int],
    card_type: str | None = None,
    top_n: int = 5,
) -> list[dict]:
    """
    규칙 기반 카드 추천 함수

    Args:
        spending  : 카테고리별 월 지출 {"음식/카페": 200000, ...}
        card_type : "credit" | "debit" | None(전체)
        top_n     : 반환할 추천 카드 수

    Returns:
        순위가 매겨진 카드 추천 결과 리스트 (top_n개)
    """
    # DB에서 데이터 로드
    cards_df, benefits_df = _load_data(card_type)

    if cards_df.empty:
        return []  # 크롤링 전이거나 DB 오류

    # 전체 카드에 대해 혜택 점수 계산
    scores = []
    for _, card in cards_df.iterrows():
        score = _calc_card_score(card, benefits_df, spending)
        scores.append(score)

    # 연 순 혜택 기준 내림차순 정렬 (혜택이 가장 큰 카드가 1위)
    scores.sort(key=lambda x: x["net_annual_benefit"], reverse=True)

    # 상위 top_n개에 순위(rank) 부여
    results = []
    for rank, score in enumerate(scores[:top_n], start=1):
        score["rank"] = rank
        results.append(score)

    return results


# ── ML 추천 영역 (개발 예정) ───────────────────────────────
# 현재는 규칙 기반 recommend_cards()를 그대로 호출합니다.
# 향후 Jupyter notebook에서 개발한 ML 모델 로직을 이 함수에 이식할 예정입니다.
def recommend_cards_ml(
    spending: dict[str, int],
    card_type: str | None = None,
    top_n: int = 5,
) -> list[dict]:
    """
    ML 기반 카드 추천 (Jupyter notebook 로직 이식 예정)
    현재는 규칙 기반 추천과 동일하게 동작합니다.
    """
    return recommend_cards(spending, card_type, top_n)
