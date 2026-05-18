"""
crawler/card_detail.py — KB카드 상세 페이지 크롤러
===================================================
Selenium 없이 requests + BeautifulSoup만으로 정적 HTML을 파싱합니다.
KB카드 상세 페이지의 탭별 HTML 구조:

  URL: https://card.kbcard.com/CRD/DVIEW/HCAMCXPRICAC0076?cooperationcode=XXX

  탭 구조 (ul.tabType1):
    #tabCon00 (주요혜택)  → .benefitList1 li 에서 혜택률, 한도 추출
    #tabCon01 (상세혜택)  → table.tblH tbody tr (주요혜택 없을 때 fallback)
    #tabCon02 (이용안내)  → 사용하지 않음
    #tabCon03 (연회비)    → table.tblH tbody tr 에서 연회비 추출
    #tabCon04 (안내사항)  → 텍스트에서 전월실적 구간 추출

Selenium vs requests 선택 이유:
  - 상세 페이지는 서버사이드 렌더링(SSR)으로 HTML 자체에 데이터가 있음
  - requests가 훨씬 빠르고 메모리를 적게 사용함 (Chrome 인스턴스 불필요)
  - display:none 탭도 HTML 소스에는 포함되어 있어 BeautifulSoup으로 파싱 가능
"""

import re
import logging
import requests
from bs4 import BeautifulSoup

from recommend import BENEFIT_CATEGORIES

logger = logging.getLogger(__name__)

BASE_URL   = "https://card.kbcard.com"
DETAIL_URL = f"{BASE_URL}/CRD/DVIEW/HCAMCXPRICAC0076"

# HTTP 요청 헤더: 실제 브라우저처럼 보이도록 설정
# KB카드 서버가 자동화 도구를 차단할 수 있어 브라우저 User-Agent 사용
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer":        BASE_URL,          # 이전 페이지 URL (직접 접근 차단 방지)
    "Accept-Language": "ko-KR,ko;q=0.9", # 한국어 우선
}

# 혜택 텍스트 → 카테고리 매핑 테이블
# 텍스트에 포함된 키워드를 기준으로 카테고리를 판별합니다.
CATEGORY_KEYWORDS = {
    "전가맹점":      ["전가맹점", "국내 가맹점", "해외 가맹점", "전체 가맹점", "모든 가맹점"],
    "음식/카페":     ["음식", "카페", "편의점", "배달", "식당", "레스토랑", "커피", "베이커리"],
    "주유/교통":     ["주유", "교통", "택시", "버스", "지하철", "철도", "고속도로", "EV", "전기차"],
    "쇼핑/간편결제": ["쇼핑", "간편결제", "온라인", "오픈마켓", "백화점", "마트", "KB Pay", "페이"],
    "항공/해외":     ["항공", "해외", "여행", "면세", "호텔", "해외가맹점"],
    "교육/건강":     ["교육", "학원", "건강", "병원", "약국", "헬스", "피트니스"],
    "자동납부":      ["자동납부", "공과금", "통신요금", "보험료", "아파트관리비"],
    "통신":          ["통신", "휴대폰", "인터넷", "SKT", "KT", "LGU+", "알뜰폰"],
    "Biz/공공":      ["Biz", "공공", "사업자", "법인", "세금", "국세", "지방세"],
}


def crawl_card_detail(cooperation_code: str) -> dict | None:
    """
    카드 1개의 상세 페이지를 크롤링합니다.

    Args:
        cooperation_code: 카드 고유 코드 (예: "09060")

    Returns:
        {
            "annual_fee_domestic": int | None,   # 국내 연회비
            "annual_fee_overseas": int | None,   # 해외 연회비
            "min_spending_1": int | None,         # 전월실적 1구간
            "min_spending_2": int | None,         # 전월실적 2구간
            "min_spending_3": int | None,         # 전월실적 3구간
            "image_url": str,                     # 카드 이미지 URL
            "benefits": [...]                     # 혜택 목록
        }
        실패 시 None 반환

    실행 순서:
      1. requests.get()으로 HTML 다운로드
      2. BeautifulSoup으로 파싱 트리 생성
      3. 각 탭에서 정보 추출 (_extract_* 함수들 호출)
    """
    url = f"{DETAIL_URL}?cooperationcode={cooperation_code}"

    try:
        logger.info(f"[{cooperation_code}] 카드 상세 크롤링 시작")

        # 1단계: HTTP GET 요청으로 HTML 다운로드
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()   # 4xx/5xx 응답이면 예외 발생
        resp.encoding = "utf-8"   # 한글 깨짐 방지

        # 2단계: HTML을 BeautifulSoup 파싱 트리로 변환
        # "lxml": 빠른 C 기반 파서 (requirements.txt에 lxml 포함)
        soup = BeautifulSoup(resp.text, "lxml")

        # 결과 초기화
        result = {
            "annual_fee_domestic": None,
            "annual_fee_overseas": None,
            "min_spending_1": None,
            "min_spending_2": None,
            "min_spending_3": None,
            "image_url": "",
            "benefits": [],
        }

        # 3단계: 각 영역에서 정보 추출
        result["image_url"] = _extract_image(soup)
        result["annual_fee_domestic"], result["annual_fee_overseas"] = _extract_annual_fee(soup)
        result["min_spending_1"], result["min_spending_2"], result["min_spending_3"] = \
            _extract_spending_tiers(soup)
        result["benefits"] = _extract_benefits(soup)

        logger.info(
            f"[{cooperation_code}] 완료 - 혜택 {len(result['benefits'])}개 / "
            f"연회비 {result['annual_fee_domestic']}원 / "
            f"전월실적 {result['min_spending_1']}/{result['min_spending_2']}/{result['min_spending_3']}원"
        )
        return result

    except requests.RequestException as e:
        logger.error(f"[{cooperation_code}] HTTP 요청 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"[{cooperation_code}] 크롤링 실패: {e}")
        return None


# ── 이미지 추출 ─────────────────────────────────────────────

def _extract_image(soup: BeautifulSoup) -> str:
    """
    카드 이미지 URL을 추출합니다.

    여러 CSS 선택자를 순서대로 시도하고 처음 찾은 이미지를 반환합니다.
    lazy-load 방식(data-src)도 처리합니다.
    """
    for selector in [
        ".card-box__card img",  # 카드 상세의 메인 이미지 영역
        "#tabCon00 img",        # 주요혜택 탭의 이미지
        ".cardImg img",         # 카드 이미지 전용 클래스
        ".card_img img",
        "img",                  # 최후 fallback: 페이지 첫 번째 이미지
    ]:
        img = soup.select_one(selector)
        if img:
            # lazy-load 처리: data-src → data-lazy-src → src 순서로 시도
            # 많은 사이트가 초기 로드 속도를 위해 실제 src 대신 data-src에 URL을 저장
            src = (
                img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("src")
                or ""
            )
            # data: 로 시작하면 base64 인코딩된 플레이스홀더 → 제외
            if src and not src.startswith("data:"):
                return src if src.startswith("http") else BASE_URL + src
    return ""


# ── 연회비 추출 ─────────────────────────────────────────────

def _extract_annual_fee(soup: BeautifulSoup) -> tuple[int | None, int | None]:
    """
    연회비 탭(#tabCon03)에서 국내/해외 연회비를 추출합니다.

    반환: (국내연회비, 해외연회비)
    예) (15000, 15000) 또는 (7000, None)

    추출 방식:
      1차: #tabCon03 table.tblH tbody tr 에서 "일반" 행 찾기
      2차 (fallback): 페이지 전체 텍스트에서 정규식으로 검색
    """
    domestic = None
    overseas = None

    # 1차 시도: 연회비 탭의 테이블에서 추출
    tab = soup.select_one("#tabCon03")
    if tab:
        rows = tab.select("table.tblH tbody tr")
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.select("td, th")]
            if not cells:
                continue
            # "일반" 이 포함된 행이 기본 연회비 행
            if any("일반" in c for c in cells):
                val = _parse_korean_amount(cells[-1])  # 마지막 셀이 금액
                if val and val >= 1000:  # 200원처럼 잘못된 값 필터링
                    domestic = val
                break

    # 2차 시도 (fallback): 전체 텍스트에서 연회비 패턴 검색
    if domestic is None:
        body_text = soup.get_text()
        for pattern in [
            r"기본연회비\s*([\d,]+)\s*원",
            r"연회비\s*[^\d]*([\d,]+)\s*원",
        ]:
            m = re.search(pattern, body_text)
            if m:
                val = int(m.group(1).replace(",", ""))
                if val >= 1000:
                    domestic = val
                    break

    return domestic, overseas


def _parse_korean_amount(text: str) -> int | None:
    """
    한국어 금액 표현을 정수로 변환합니다.

    예:
      "7천원"    → 7000
      "5만5천원" → 55000
      "2억원"    → 200000000
      "없음"     → None
      "-"        → None

    동작 방식:
      "억" → "만" → "천" → 나머지 순서로 파싱하여 합산
    """
    text = text.replace(",", "").replace("원", "").replace(" ", "").strip()
    if not text or text in ("없음", "-", ""):
        return None

    total = 0
    t = text

    # 억 단위 처리 (예: "1억" → 100,000,000)
    if "억" in t:
        p = t.split("억")
        total += int(p[0]) * 100_000_000
        t = p[1]

    # 만 단위 처리 (예: "5만" → 50,000)
    if "만" in t:
        p = t.split("만")
        total += int(p[0]) * 10_000
        t = p[1]

    # 천 단위 처리 (예: "5천" → 5,000)
    if "천" in t:
        p = t.split("천")
        total += int(p[0]) * 1_000
        t = p[1]

    # 나머지 숫자 처리
    if t.isdigit():
        total += int(t)

    return total if total > 0 else None


# ── 전월실적 추출 ────────────────────────────────────────────

# 한국어 금액 정규식 패턴 (모듈 레벨 상수로 정의해 재사용)
# 예: "30만원", "5만5천원", "100만원"
_KRW = r"\d+\s*만\s*(?:\d+\s*천\s*)?원?"


def _extract_spending_tiers(soup: BeautifulSoup) -> tuple[int | None, int | None, int | None]:
    """
    안내사항 탭(#tabCon04)에서 전월실적 구간 금액을 추출합니다.

    반환: (tier1, tier2, tier3) — 오름차순 정렬, 없으면 None
    최대 3구간까지 지원합니다.

    예:
      "40만원 이상 / 80만원 이상 / 120만원 이상" → (400000, 800000, 1200000)
      "30만원 이상"                               → (300000, None, None)
      "전월실적 조건 없음"                         → (None, None, None)

    여러 패턴을 순차적으로 시도합니다 (1→2→3→4→5→실패 로깅):
      1. 아라비아 숫자 + "이상" 패턴
      2. 한국어 단위(만/천) + "이상" 패턴
      3. "N구간(XX만원 이상)" 패턴
      4. "전월 실적 별" 키워드 이후 금액
      5. "XX만원 미만" 패턴
    """
    # 안내사항 탭에서 텍스트 추출 (없으면 전체 페이지 텍스트 사용)
    tab = soup.select_one("#tabCon04")
    text = tab.get_text() if tab else soup.get_text()

    # 전월실적 조건 없음 패턴 확인
    no_req = [
        r"전월\s*실적\s*조건\s*없음",
        r"전월\s*실적\s*한도\s*없이",
        r"실적\s*조건\s*및.*없음",
        r"전월\s*실적\s*채워\s*드림",
    ]
    for p in no_req:
        if re.search(p, text):
            return None, None, None  # 실적 조건 없는 카드

    tiers: list[int] = []

    def _valid(vals):
        """10,000원 미만 값을 제거하고 중복 제거 후 정렬"""
        return sorted({v for v in vals if v and v >= 10000})

    # 1) 아라비아 숫자 형태: "전월실적 300,000원 이상"
    arabic = re.findall(
        r"전월\s*(?:실적|이용실적|이용금액)\s*([\d,]+)\s*원\s*이상", text
    )
    if arabic:
        tiers = _valid([int(v.replace(",", "")) for v in arabic])

    # 2) 한국어 금액 형태: "전월실적 30만원 이상"
    if not tiers:
        krw_이상 = re.findall(rf"({_KRW})\s*이상", text)
        tiers = _valid([_parse_korean_amount(v) for v in krw_이상])

    # 3) 구간 표현: "1구간(30만원 이상) 2구간(70만원 이상)"
    if not tiers:
        구간 = re.findall(rf"\d+구간\s*[\(（]\s*({_KRW})\s*이상", text)
        tiers = _valid([_parse_korean_amount(v) for v in 구간])

    # 4) "전월 실적 별" 키워드 이후 금액 나열
    if not tiers:
        별_m = re.search(r"전월\s*실적\s*별", text)
        if 별_m:
            # 키워드 이후 300자 내에서 금액 찾기
            context = text[별_m.start(): 별_m.start() + 300]
            paren = re.findall(rf"[\(（]({_KRW})[\)）]", context)
            if paren:
                tiers = _valid([_parse_korean_amount(v) for v in paren])
            if not tiers:
                bare = re.findall(rf"({_KRW})", context)
                tiers = _valid([_parse_korean_amount(v) for v in bare])

    # 5) "미만" 표현: "40만원 미만" → 40만원이 1구간 기준
    if not tiers:
        미만_m = re.search(rf"전월\s*(?:실적|이용실적)\s*({_KRW})\s*미만", text)
        if 미만_m:
            v = _parse_korean_amount(미만_m.group(1))
            if v and v >= 10000:
                tiers = [v]

    # 패턴 미매칭 시 컨텍스트 로깅 (디버깅용)
    if not tiers:
        for kw in ["전월실적", "전월 실적", "이용실적"]:
            idx = text.find(kw)
            if idx != -1:
                logger.info(f"전월 컨텍스트(패턴미매칭): ...{text[idx:idx+80]}...")
                break

    # 최대 3구간만 반환 (나머지는 None으로 채움)
    t = (tiers + [None, None, None])[:3]
    return t[0], t[1], t[2]


# ── 혜택 추출 ───────────────────────────────────────────────

def _extract_benefits(soup: BeautifulSoup) -> list[dict]:
    """
    주요혜택 탭(#tabCon00)에서 혜택 목록을 추출합니다.

    1차: #tabCon00 .benefitList1 li (주요 혜택 리스트)
    2차 (fallback): #tabCon01 table.tblH tbody tr (상세 혜택 테이블)
    """
    benefits = []

    # 주요혜택 탭의 혜택 리스트에서 추출
    tab = soup.select_one("#tabCon00")
    items = tab.select(".benefitList1 li") if tab else soup.select(".benefitList1 li")

    for item in items:
        benefit = _parse_benefit_item(item)
        if benefit:
            benefits.append(benefit)

    # 주요혜택이 없으면 상세혜택 테이블에서 fallback
    if not benefits:
        benefits = _extract_benefits_from_table(soup)

    return benefits


def _extract_max_amounts(text: str) -> tuple[int | None, int | None, int | None]:
    """
    혜택 설명 텍스트에서 구간별 월 최대 혜택 금액을 추출합니다.

    반환: (max1, max2, max3) — 오름차순

    예:
      "최대 1만원"       → (10000, None, None)
      "1만원/2만원/3만원" → (10000, 20000, 30000)
      "1만원 2만원"       → (10000, 20000, None)
    """
    # 한국어 금액 패턴으로 모든 금액 추출
    krw_amounts = re.findall(rf"({_KRW})", text)
    vals = []
    for raw in krw_amounts:
        v = _parse_korean_amount(raw)
        if v and v >= 1000:  # 100원 단위 오탐 방지
            vals.append(v)

    # 아라비아 숫자 금액도 추출 (예: "15,000원")
    arabic_amounts = re.findall(r"([\d,]+)\s*원", text)
    for raw in arabic_amounts:
        v = int(raw.replace(",", ""))
        if v >= 1000:
            vals.append(v)

    # 중복 제거 후 오름차순 정렬
    vals = sorted(set(vals))

    # "최대" 키워드가 있으면 단일 최대값으로 처리
    if re.search(r"최대", text) and vals:
        m = max(vals)
        return m, None, None

    # 최대 3개 반환
    t = (vals + [None, None, None])[:3]
    return t[0], t[1], t[2]


def _parse_rate(raw: str) -> tuple[float | None, float | None]:
    """
    혜택률 텍스트를 (최솟값, 최댓값) 형태로 변환합니다.

    예:
      "5%"    → (5.0, 5.0)
      "5~30%" → (5.0, 30.0)
      "5~30"  → (5.0, 30.0)
      "최대"   → (None, None)  ← 숫자가 아닌 텍스트
    """
    raw = raw.strip()

    # 범위 패턴: "5~30%" 또는 "5~30" 또는 "0.2~0.5"
    range_m = re.match(r"^([\d.]+)\s*[~～]\s*([\d.]+)\s*%?$", raw)
    if range_m:
        return float(range_m.group(1)), float(range_m.group(2))

    # 단일 값: "5%" 또는 "5"
    single_m = re.match(r"^([\d.]+)\s*%?$", raw)
    if single_m:
        v = float(single_m.group(1))
        return v, v  # 단일 값은 min=max

    # 숫자가 아닌 텍스트 ("최대", "전월실적채워드림" 등)
    return None, None


def _parse_benefit_item(item) -> dict | None:
    """
    .benefitList1 li 요소 1개에서 혜택 정보를 파싱합니다.

    HTML 구조 예시:
      <li>
        <strong class="tit">음식/카페</strong>
        <span class="txt">월 최대 <em>10%</em> 할인</span>
      </li>

    반환: 혜택 dict 또는 None (혜택률을 찾지 못한 경우)
    """
    try:
        # 카테고리 텍스트 (strong.tit)
        tit = item.select_one("strong.tit")
        if not tit:
            return None
        category_text = tit.get_text(strip=True)

        # 혜택 설명 텍스트 (span.txt)
        txt_span = item.select_one("span.txt")
        if not txt_span:
            return None
        full_text = txt_span.get_text(strip=True)

        rate_min, rate_max = None, None

        # em 태그에서 혜택률 우선 추출 (예: <em>10%</em>)
        em = txt_span.select_one("em")
        if em:
            em_raw = em.get_text(strip=True)
            rate_min, rate_max = _parse_rate(em_raw)

        # em 태그 실패 시 전체 텍스트에서 % 패턴으로 추출
        if rate_min is None:
            # 범위 패턴 우선
            m = re.search(r"([\d.]+)\s*[~～]\s*([\d.]+)\s*%", full_text)
            if m:
                rate_min, rate_max = float(m.group(1)), float(m.group(2))
            else:
                # 단일 % 패턴
                m = re.search(r"([\d.]+)\s*%", full_text)
                if m:
                    rate_min = rate_max = float(m.group(1))

        # 혜택률을 찾지 못했으면 None 반환
        if rate_min is None:
            return None

        # 혜택 유형 판단: "적립" 텍스트가 있으면 적립, 없으면 할인
        benefit_type = "reward" if "적립" in full_text else "discount"

        # 카테고리 분류 (키워드 매핑 테이블 사용)
        category = _classify_category(category_text + " " + full_text)

        # 구간별 최대 혜택 금액 추출
        max_amount_1, max_amount_2, max_amount_3 = _extract_max_amounts(full_text)

        return {
            "category":     category,
            "benefit_type": benefit_type,
            "rate_min":     rate_min,
            "rate_max":     rate_max,
            "max_amount_1": max_amount_1,
            "max_amount_2": max_amount_2,
            "max_amount_3": max_amount_3,
            "conditions":   "",
            "description":  full_text[:300],  # 최대 300자로 제한
        }

    except Exception as e:
        logger.error(f"혜택 항목 파싱 오류: {e}")
        return None


def _extract_benefits_from_table(soup: BeautifulSoup) -> list[dict]:
    """
    상세혜택 테이블(#tabCon01 table.tblH tbody tr)에서 혜택을 추출합니다.

    .benefitList1이 없는 카드에서 사용하는 fallback 방식입니다.
    테이블 첫 번째 열 = 카테고리, 두 번째 열 = 혜택률
    """
    benefits = []
    try:
        tab = soup.select_one("#tabCon01")
        if not tab:
            return benefits

        rows = tab.select("table.tblH tbody tr")
        for row in rows:
            tds = row.select("td")
            if len(tds) < 2:
                continue

            category_text = tds[0].get_text(strip=True)
            rate_text     = tds[1].get_text(strip=True)

            rate_min, rate_max = None, None

            # 범위 패턴 우선 시도
            rm = re.search(r"([\d.]+)\s*[~～]\s*([\d.]+)\s*%", rate_text)
            if rm:
                rate_min, rate_max = float(rm.group(1)), float(rm.group(2))
            else:
                sm = re.search(r"([\d.]+)\s*%", rate_text)
                if sm:
                    rate_min = rate_max = float(sm.group(1))

            if rate_min is None:
                continue  # 혜택률 없는 행은 건너뜀

            benefit_type = "reward" if "적립" in rate_text else "discount"
            category     = _classify_category(category_text)

            # 테이블 전체 행 텍스트에서 최대 혜택 금액 추출
            full_row_text = " ".join(td.get_text(strip=True) for td in tds)
            max_amount_1, max_amount_2, max_amount_3 = _extract_max_amounts(full_row_text)

            benefits.append({
                "category":     category,
                "benefit_type": benefit_type,
                "rate_min":     rate_min,
                "rate_max":     rate_max,
                "max_amount_1": max_amount_1,
                "max_amount_2": max_amount_2,
                "max_amount_3": max_amount_3,
                "conditions":   "",
                "description":  f"{category_text} {rate_text}",
            })

    except Exception as e:
        logger.error(f"테이블 혜택 파싱 오류: {e}")

    return benefits


def _classify_category(text: str) -> str:
    """
    텍스트에서 혜택 카테고리를 분류합니다.

    CATEGORY_KEYWORDS 딕셔너리의 키워드와 텍스트를 비교하여
    가장 먼저 매칭되는 카테고리를 반환합니다.
    매칭되는 카테고리가 없으면 "전가맹점"으로 분류합니다.
    """
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category
    return "전가맹점"  # 매칭 실패 시 기본값
