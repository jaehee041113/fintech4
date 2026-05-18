"""
crawler/base.py — Selenium Chrome 드라이버 팩토리
===================================================
카드 목록 크롤링에 사용할 Chrome 브라우저 인스턴스를 생성합니다.

실행 환경에 따라 두 가지 방식으로 드라이버를 생성합니다:
  - Docker 환경 : 이미 설치된 시스템 Chromium 사용 (환경변수로 경로 지정)
  - 로컬 환경   : webdriver-manager가 적합한 ChromeDriver를 자동 다운로드
"""

import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Selenium Chrome 드라이버를 생성하고 반환합니다.

    Args:
        headless: True이면 브라우저 창 없이 백그라운드에서 실행 (서버 환경 기본값)
                  False이면 실제 브라우저 창이 열림 (디버깅 시 유용)

    Returns:
        설정이 완료된 webdriver.Chrome 인스턴스

    실행 순서:
      1. Chrome 옵션(Options) 설정
      2. 환경변수 CHROME_BIN 확인
         - 있으면 Docker 모드: 시스템 Chromium 경로 사용
         - 없으면 로컬 모드: webdriver-manager로 자동 다운로드
      3. Service + Options로 Chrome 드라이버 생성 후 반환
    """

    # ── Chrome 옵션 설정 ──────────────────────────────────────
    options = Options()

    if headless:
        # 브라우저 창 없이 실행 (서버에서 필수)
        options.add_argument("--headless=new")

    # Docker/Linux 환경에서 Chrome 실행 시 필요한 보안 설정
    options.add_argument("--no-sandbox")            # 샌드박스 비활성화 (root 실행 허용)
    options.add_argument("--disable-dev-shm-usage") # 공유 메모리 대신 /tmp 사용 (메모리 부족 방지)
    options.add_argument("--disable-gpu")           # GPU 가속 비활성화 (서버 환경)
    options.add_argument("--window-size=1920,1080") # 가상 화면 크기 지정

    # 한국어 환경 설정 (KB카드 사이트 정상 렌더링을 위해)
    options.add_argument("--lang=ko-KR")

    # 실제 사용자 브라우저처럼 보이게 User-Agent 설정
    # → 일부 사이트는 자동화 도구를 차단하므로 일반 브라우저로 위장
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # 브라우저 자동화 감지 방지 옵션
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # ── 환경별 드라이버 생성 ──────────────────────────────────
    chrome_bin = os.getenv("CHROME_BIN")           # Docker: /usr/bin/chromium
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")  # Docker: /usr/bin/chromedriver

    if chrome_bin:
        # Docker 환경: Dockerfile에서 설치한 시스템 Chromium 사용
        options.binary_location = chrome_bin
        service = Service(executable_path=chromedriver_path or "/usr/bin/chromedriver")
    else:
        # 로컬 환경: webdriver-manager가 현재 Chrome 버전에 맞는 드라이버를 자동 다운로드
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    # Chrome 드라이버 생성
    driver = webdriver.Chrome(service=service, options=options)

    # 요소를 찾을 때 최대 10초 대기 (페이지 로딩 시간 여유)
    driver.implicitly_wait(10)

    return driver
