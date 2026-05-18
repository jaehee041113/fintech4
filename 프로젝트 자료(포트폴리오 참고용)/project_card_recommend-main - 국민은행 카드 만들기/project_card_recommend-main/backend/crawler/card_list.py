"""
card_list.py — KB국민카드 카드 목록 크롤러
==========================================
KB국민카드 웹사이트에서 신용카드/체크카드 목록을 수집합니다.

[수집 대상 페이지]
  - 신용카드: https://card.kbcard.com/CRD/DVIEW/HCAMCXPRICAC0047
  - 체크카드: https://card.kbcard.com/CRD/DVIEW/HCAMCXPRICAC0056

[크롤링 방식]
  - Selenium: KB 카드 목록 페이지는 JavaScript로 동적 렌더링됨
    → 일반 requests로는 카드 목록을 가져올 수 없음
    → Selenium이 실제 브라우저처럼 JS를 실행한 후 DOM을 읽음

[탭 구조]
  신용카드 페이지: 전가맹점 / 음식·카페 / 주유·교통 / 쇼핑·간편결제 / 항공·해외 / 교육·건강 / 자동납부 / 통신 / Biz·공공 (총 9개 탭)
  체크카드 페이지: 전가맹점 / 음식·카페 / 주유·교통 / 쇼핑·간편결제 / 교육·건강 / 자동납부 / 통신 (총 7개 탭)

  각 탭은 해당 혜택 카테고리에서 혜택을 제공하는 카드만 표시합니다.
  → 모든 탭을 순회해야 전체 카드를 빠짐없이 수집할 수 있습니다.

[중복 제거]
  하나의 카드가 여러 탭에 동시에 표시될 수 있습니다.
  → cooperation_code를 딕셔너리 키로 사용해 자동 중복 제거

[다음 단계]
  수집한 카드 목록 → card_detail.py에서 각 카드의 상세 혜택 정보 수집
  → run_crawler.py에서 두 단계를 통합 실행
"""

import re
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base import create_driver  # Chrome 드라이버 생성 함수 (base.py)

# 이 모듈의 로거 설정
# logging.getLogger(__name__): 모듈 이름("crawler.card_list")으로 로거 생성
# 로그 레벨/형식은 run_crawler.py에서 설정
logger = logging.getLogger(__name__)

# ── 수집 대상 URL ────────────────────────────────────────────
# card_type 문자열("credit" / "debit")을 키로, URL을 값으로 매핑
CARD_LIST_URLS = {
    "credit": "https://card.kbcard.com/CRD/DVIEW/HCAMCXPRICAC0047",  # 신용카드 목록
    "debit":  "https://card.kbcard.com/CRD/DVIEW/HCAMCXPRICAC0056",  # 체크카드 목록
}

# 상대 경로 이미지 URL을 절대 경로로 변환할 때 사용하는 기본 도메인
BASE_URL = "https://card.kbcard.com"


def crawl_card_list(card_type: str) -> list[dict]:
    """
    카드 목록 페이지에서 카드 기본 정보 수집

    [처리 흐름]
      1. Selenium Chrome 드라이버 실행 (headless 모드: 화면 없이 실행)
      2. 카드 목록 페이지 접속
      3. 혜택 카테고리 탭 목록 파악
      4. 각 탭을 클릭하며 카드 목록 수집 (cooperation_code로 중복 제거)
      5. 드라이버 종료 후 결과 반환

    Args:
        card_type: "credit" (신용카드) 또는 "debit" (체크카드)

    Returns:
        카드 정보 딕셔너리 목록:
        [
            {
                "name": "KB국민 MY WE:SH카드",        # 카드명
                "card_type": "credit",               # 카드 종류
                "description": "전 가맹점 0.7% 적립", # 카드 설명 (뱃지 문구)
                "image_url": "https://...",           # 카드 이미지 URL
                "detail_url": "https://...",          # 카드 상세 페이지 URL
                "cooperation_code": "09297"           # KB 내부 카드 고유 코드
            },
            ...
        ]
    """
    url = CARD_LIST_URLS[card_type]

    # headless=True: 화면 없이 백그라운드에서 Chrome 실행
    # Docker 환경(GUI 없음)에서 필수
    driver = create_driver(headless=True)

    # cooperation_code → 카드 정보 딕셔너리
    # 딕셔너리를 사용하면 같은 코드로 카드가 다시 들어와도 덮어쓰지 않고 무시 가능
    cards_by_code: dict[str, dict] = {}

    try:
        logger.info(f"[{card_type}] 카드 목록 크롤링 시작: {url}")
        driver.get(url)  # 브라우저로 해당 URL 접속

        # WebDriverWait: 특정 조건이 만족될 때까지 최대 30초 대기
        # 페이지 JS 렌더링이 완료될 때까지 기다리기 위해 사용
        wait = WebDriverWait(driver, 30)

        # 카드 목록(.card-box__item)이 화면에 나타날 때까지 대기
        try:
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".card-box__item"))
            )
        except TimeoutException:
            # 30초 안에 카드가 안 나타나도 일단 진행 (페이지에 카드가 없을 수 있음)
            logger.warning(f"[{card_type}] 초기 로딩 타임아웃, 현재 상태로 진행")

        # ── 혜택 카테고리 탭 목록 수집 ──────────────────────────
        # HTML 구조:
        #   <ul class="tabs__menu">
        #     <li id="benefit_01"><a>전 가맹점</a></li>
        #     <li id="benefit_02"><a>음식·카페</a></li>
        #     ...
        #   </ul>
        # "id^='benefit_'": id가 "benefit_"으로 시작하는 li 요소만 선택
        tab_links = driver.find_elements(
            By.CSS_SELECTOR, "ul.tabs__menu li[id^='benefit_'] a"
        )
        if not tab_links:
            # 탭이 없는 경우: 현재 화면에 보이는 카드만 수집
            tab_links = []

        tab_count = len(tab_links)
        logger.info(f"[{card_type}] 혜택 탭 {tab_count}개 발견")

        def collect_current_tab():
            """
            현재 활성화된 탭에 표시된 카드를 모두 수집하여 cards_by_code에 추가

            [처리 흐름]
              1. 탭 전환 후 카드 목록 렌더링 완료 대기
              2. 모든 .card-box__item 요소 탐색
              3. 각 요소에서 카드 정보 추출 (_extract_card 호출)
              4. cooperation_code 중복 확인 후 딕셔너리에 추가

            Returns:
                이번 탭에서 새로 추가된 카드 수
            """
            try:
                # 탭 클릭 후 카드 목록이 새로 렌더링될 때까지 대기
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card-box__item"))
                )
            except TimeoutException:
                pass  # 타임아웃이어도 현재 상태로 진행

            # 현재 탭에 표시된 모든 카드 요소 수집
            elements = driver.find_elements(By.CSS_SELECTOR, ".card-box__item")
            added = 0  # 이번 탭에서 새로 추가된 카드 수 카운트

            for el in elements:
                try:
                    # _extract_card: Selenium 요소에서 카드 정보 딕셔너리 추출
                    info = _extract_card(el, card_type)

                    # 유효한 카드 정보이고, 아직 수집하지 않은 카드인 경우에만 추가
                    if info and info["cooperation_code"] not in cards_by_code:
                        cards_by_code[info["cooperation_code"]] = info
                        added += 1
                except Exception as e:
                    logger.error(f"[{card_type}] 카드 요소 파싱 오류: {e}")

            return added

        # ── 탭 순회 또는 단일 페이지 수집 ───────────────────────
        if tab_count == 0:
            # 탭이 없는 경우: 현재 페이지에 표시된 카드만 수집
            collect_current_tab()
        else:
            # 탭이 있는 경우: 각 탭을 차례로 클릭하며 수집
            for i in range(tab_count):
                # 탭을 클릭하면 DOM이 갱신될 수 있으므로
                # 매 반복마다 탭 요소를 새로 조회해야 함
                # (이전에 저장한 탭 요소 참조는 DOM 갱신 후 무효화됨 — StaleElementReferenceException)
                tabs = driver.find_elements(
                    By.CSS_SELECTOR, "ul.tabs__menu li[id^='benefit_'] a"
                )
                if i >= len(tabs):
                    break  # 예상보다 탭이 적은 경우 종료

                tab = tabs[i]
                tab_name = tab.text.strip() or f"탭{i+1}"  # 탭 이름 (로그 출력용)

                try:
                    # JavaScript로 클릭: 일반 .click()은 화면 밖 요소에서 실패할 수 있음
                    # execute_script로 직접 클릭 이벤트 발생
                    driver.execute_script("arguments[0].click();", tab)

                    import time as _time
                    _time.sleep(1)  # 탭 클릭 후 JS 렌더링 완료 대기 (1초)
                    # WebDriverWait을 쓰는 것이 더 정확하지만,
                    # 탭 전환 완료 조건이 명확하지 않아 sleep으로 처리
                except Exception as e:
                    logger.warning(f"[{card_type}] 탭 '{tab_name}' 클릭 실패: {e}")
                    continue  # 탭 클릭 실패 시 다음 탭으로

                added = collect_current_tab()
                logger.info(f"[{card_type}] 탭 '{tab_name}' → 신규 카드 {added}개")

        # 딕셔너리 값만 리스트로 변환하여 반환
        cards = list(cards_by_code.values())
        logger.info(f"[{card_type}] 총 {len(cards)}개 카드 수집 완료")

    except Exception as e:
        logger.error(f"[{card_type}] 카드 목록 크롤링 실패: {e}")
        cards = []  # 오류 발생 시 빈 리스트 반환

    finally:
        # 성공/실패 관계없이 항상 브라우저 종료
        # finally 블록은 try/except 이후 반드시 실행됨
        driver.quit()

    return cards


def _extract_card(element, card_type: str) -> dict | None:
    """
    Selenium WebElement(.card-box__item)에서 카드 정보를 추출

    [HTML 구조 예시]
      <div class="card-box__item">
        <a class="linkDetail" onclick="javascript:goDetail('09297','')">
          <div class="tit-dep4">KB국민 MY WE:SH카드</div>       ← 카드명
          <span class="badge--txt">전 가맹점 0.7% 적립</span>    ← 카드 설명
          <img data-src="/images/card/09297_img.png" .../>       ← 카드 이미지 (lazy-load)
        </a>
      </div>

    [cooperation_code 추출 방법]
      onclick 속성값: "javascript:goDetail('09297','')"
      정규표현식: r"goDetail\('([^']+)'"
        - \(  : 리터럴 "(" 문자
        - '   : 리터럴 "'" 문자
        - ([^']+): 따옴표가 아닌 문자 1개 이상 → 캡처 그룹 = cooperation_code
        - '   : 리터럴 "'" 문자
      → match.group(1) = "09297"

    Args:
        element:   Selenium WebElement (.card-box__item 요소)
        card_type: "credit" 또는 "debit"

    Returns:
        카드 정보 딕셔너리, 또는 필수 정보 없으면 None
    """
    try:
        # ── 카드명 추출 ──────────────────────────────────────
        # .tit-dep4: KB 카드 목록 페이지에서 카드명을 감싸는 CSS 클래스
        name = ""
        try:
            name = element.find_element(By.CSS_SELECTOR, ".tit-dep4").text.strip()
        except NoSuchElementException:
            pass  # 카드명이 없는 요소는 나중에 None 반환으로 필터링

        # ── 카드 설명 추출 ───────────────────────────────────
        # .badge--txt: 카드 목록 페이지의 뱃지 형태로 표시되는 카드 핵심 혜택 문구
        # 예: "전 가맹점 0.7% 적립", "생활 쇼핑 최대 5% 청구할인"
        description = ""
        try:
            description = element.find_element(By.CSS_SELECTOR, ".badge--txt").text.strip()
        except NoSuchElementException:
            pass  # 설명이 없어도 계속 진행 (선택 항목)

        # ── 카드 이미지 URL 추출 ─────────────────────────────
        # KB 카드 목록은 이미지 lazy-loading을 사용:
        #   <img data-src="/images/..." src="data:image/gif;base64,...">
        # → 화면에 보이기 전에는 src가 투명 1px GIF임
        # → 실제 이미지 URL은 data-src 또는 data-lazy-src에 저장됨
        #
        # 우선순위: data-src → data-lazy-src → src
        # "data:"로 시작하는 src는 플레이스홀더이므로 제외
        image_url = ""
        try:
            img = element.find_element(By.CSS_SELECTOR, "img")
            src = (
                img.get_attribute("data-src")       # 1순위: lazy-load용 실제 URL
                or img.get_attribute("data-lazy-src")  # 2순위: 다른 lazy-load 방식
                or img.get_attribute("src")          # 3순위: 일반 src
                or ""
            )
            if src and not src.startswith("data:"):
                # 상대 경로인 경우 절대 경로로 변환
                # 예: "/images/card/09297_img.png" → "https://card.kbcard.com/images/..."
                image_url = src if src.startswith("http") else BASE_URL + src
        except NoSuchElementException:
            pass  # 이미지 없는 카드는 image_url = "" 로 처리

        # ── cooperation_code 및 상세 페이지 URL 추출 ─────────
        # cooperation_code: KB 카드 시스템에서 카드를 고유하게 식별하는 숫자 코드
        # 예: "09297", "09060"
        #
        # detail_url: 카드 상세 페이지 URL 패턴
        # https://card.kbcard.com/CRD/DVIEW/HCAMCXPRICAC0076?cooperationcode={code}
        cooperation_code = ""
        detail_url = ""
        try:
            # a.linkDetail: 카드 전체를 감싸는 링크 요소
            link = element.find_element(By.CSS_SELECTOR, "a.linkDetail")
            onclick = link.get_attribute("onclick") or ""

            # 정규표현식으로 cooperation_code 추출
            # onclick 예시: "javascript:goDetail('09297','')"
            match = re.search(r"goDetail\('([^']+)'", onclick)
            if match:
                cooperation_code = match.group(1)  # 첫 번째 캡처 그룹 = cooperation_code
                # 상세 페이지 URL 조합
                detail_url = f"{BASE_URL}/CRD/DVIEW/HCAMCXPRICAC0076?cooperationcode={cooperation_code}"
        except NoSuchElementException:
            pass

        # 카드명과 고유 코드가 없으면 유효하지 않은 요소로 판단하여 None 반환
        if not name or not cooperation_code:
            return None

        return {
            "name": name,
            "card_type": card_type,       # "credit" 또는 "debit"
            "description": description,
            "image_url": image_url,
            "detail_url": detail_url,
            "cooperation_code": cooperation_code,
        }

    except Exception as e:
        logger.error(f"카드 요소 파싱 오류: {e}")
        return None
