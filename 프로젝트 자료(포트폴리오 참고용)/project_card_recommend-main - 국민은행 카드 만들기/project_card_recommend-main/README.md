# KB국민카드 추천 서비스

KB국민카드 웹사이트를 크롤링하여 카드 정보를 수집하고, 사용자의 카테고리별 월 지출 패턴을 기반으로 최적의 카드를 추천하는 풀스택 웹 애플리케이션입니다.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | Python 3.12, FastAPI, Uvicorn |
| 크롤링 | Selenium 4 (목록), requests + BeautifulSoup4 (상세) |
| 스케줄러 | APScheduler |
| 데이터베이스 | MySQL 8.0, SQLAlchemy, PyMySQL, cryptography |
| 데이터 처리 | pandas 2.x, numpy, scikit-learn |
| 프론트엔드 | Next.js, React, TypeScript, Tailwind CSS v4 |
| 인프라 | Docker, Docker Compose, Nginx |
| 폰트 | KBFGDisplayM (KB금융 제목체, KB 서버에서 로드) |

---

## 프로젝트 구조

```
project_card_recommend/
├── backend/
│   ├── crawler/
│   │   ├── base.py            # Selenium Chrome 드라이버 팩토리
│   │   ├── card_list.py       # KB카드 목록 크롤러 (Selenium, 전체 탭 순회)
│   │   ├── card_detail.py     # KB카드 상세 크롤러 (requests + BeautifulSoup)
│   │   └── run_crawler.py     # 크롤링 진입점 (신용/체크 전체)
│   ├── scheduler/
│   │   └── crawl_scheduler.py # APScheduler 주기적 크롤링 설정
│   ├── main.py                # FastAPI 애플리케이션 및 API 엔드포인트
│   ├── dbio.py                # MySQL 연결 및 DataFrame I/O
│   ├── recommend.py           # 카드 추천 엔진 (전월실적 구간별 혜택 계산)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── api/recommend/route.ts  # Next.js 서버사이드 프록시
│   │   ├── page.tsx                # 홈 페이지
│   │   ├── layout.tsx              # 루트 레이아웃
│   │   └── globals.css             # 전역 스타일 + KBFGDisplayM 폰트
│   ├── components/
│   │   ├── SpendingForm.tsx        # 카테고리별 지출 입력 폼
│   │   └── CardResult.tsx          # 추천 카드 결과 카드 컴포넌트
│   ├── lib/
│   │   └── api.ts                  # API 타입 정의 및 fetchRecommendations
│   ├── package.json
│   ├── Dockerfile
│   └── next.config.ts
├── nginx/
│   └── nginx.conf             # 리버스 프록시 설정
├── docker-compose.yml         # 로컬 개발 환경
├── docker-compose.prod.yml    # 프로덕션 환경 (AWS EC2)
└── .env.example               # 환경변수 템플릿 (이 파일을 복사해 .env 생성)
```

---

## 아키텍처

**프로덕션 환경 (AWS EC2)**
```
[사용자 브라우저]
       │
       ▼
   [Nginx :80]
    ├── /api/*  →  [FastAPI :8000]  →  [MySQL :3306]
    ├── /docs   →  [FastAPI Swagger UI]
    └── /*      →  [Next.js :3000]
                        │
                        └── /api/recommend  →  [FastAPI :8000] (서버사이드 프록시)

[APScheduler] ─── 매주 월요일 00:00 KST ───► [Selenium 크롤러] ──► [MySQL]
```

**로컬 개발 환경** (Nginx 없음, 포트 직접 접근)
```
[사용자 브라우저]
    ├── http://localhost:3000  →  [Next.js]
    └── http://localhost:8000  →  [FastAPI]  →  [MySQL :3307]
```

---

## 데이터 흐름

1. **목록 크롤링**: Selenium(headless Chrome)으로 KB국민카드 사이트의 혜택 탭(신용 9개, 체크 7개)을 순회하며 전체 카드 수집 (신용 105개, 체크 23개)
2. **상세 크롤링**: requests + BeautifulSoup로 각 카드의 연회비, 전월실적 구간, 카테고리별 혜택률 수집
3. **저장**: pandas DataFrame으로 변환 후 MySQL에 저장 (매주 전체 교체)
4. **추천**: 사용자가 카테고리별 월 지출 금액을 입력하면, 전월실적 구간에 따른 혜택 한도를 적용하여 연 순 혜택 기준으로 랭킹

---

## DB 스키마

### `cards` 테이블

| 컬럼 | 설명 |
|------|------|
| cooperation_code | 카드 고유 코드 |
| name | 카드명 |
| card_type | `credit` (신용카드) / `debit` (체크카드) |
| description | 카드 설명 |
| detail_url | KB카드 상세 페이지 URL |
| image_url | 카드 이미지 URL (`img1.kbcard.com/…/{cooperation_code}_img.png`) |
| annual_fee_domestic | 국내 연회비 (원) |
| annual_fee_overseas | 해외 연회비 (원) |
| min_spending_1 | 전월실적 1구간 기준 금액 (원) |
| min_spending_2 | 전월실적 2구간 기준 금액 (원) |
| min_spending_3 | 전월실적 3구간 기준 금액 (원) |
| crawled_at | 크롤링 일시 |

### `card_benefits` 테이블

| 컬럼 | 설명 |
|------|------|
| cooperation_code | 카드 고유 코드 (FK) |
| category | 혜택 카테고리 |
| benefit_type | 혜택 유형 (할인/적립 등) |
| rate_min | 혜택률 최솟값 (%) — `5~30%` 이면 5.0 |
| rate_max | 혜택률 최댓값 (%) — `5~30%` 이면 30.0 |
| max_amount_1 | 전월실적 1구간 월 최대 혜택 금액 (원) |
| max_amount_2 | 전월실적 2구간 월 최대 혜택 금액 (원) |
| max_amount_3 | 전월실적 3구간 월 최대 혜택 금액 (원) |
| conditions | 혜택 조건 |
| description | 혜택 설명 |

---

## API 엔드포인트

Swagger UI: `http://localhost:8000/docs`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/cards` | 카드 목록 조회 (`?card_type=credit\|debit`) |
| GET | `/api/cards/{cooperation_code}` | 카드 상세 및 혜택 조회 |
| GET | `/api/categories` | 혜택 카테고리 목록 |
| POST | `/api/recommend` | 지출 패턴 기반 카드 추천 |
| POST | `/api/crawl/trigger` | 크롤링 수동 실행 (백그라운드) |
| GET | `/api/crawl/schedule` | 스케줄러 상태 조회 |
| GET | `/health` | 헬스체크 |

### 추천 API 요청 예시

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "spending": {
      "음식/카페": 300000,
      "주유/교통": 150000,
      "쇼핑/간편결제": 200000,
      "통신": 80000
    },
    "card_type": "credit",
    "top_n": 5
  }'
```

### 지원 카테고리

| | | |
|---|---|---|
| 전가맹점 | 음식/카페 | 주유/교통 |
| 쇼핑/간편결제 | 항공/해외 | 교육/건강 |
| 자동납부 | 통신 | Biz/공공 |

### 추천 로직

1. 총 지출액 기준 전월실적 구간 판정 (1~3구간, 미달 시 혜택 제외)
2. 카테고리별 지출 × `rate_min` = 예상 월 혜택 금액
3. 해당 구간의 `max_amount_N` 한도 적용
4. 해당 카테고리 혜택 없을 경우 `전가맹점` 혜택으로 대체
5. `연간 순 혜택 = 예상 월 혜택 × 12 - 연회비` 기준 내림차순 정렬

---

## 로컬에서 처음 실행하기

> **핵심 요약**: Docker 설치 → 코드 내려받기 → `.env` 파일 생성 → 실행 → 데이터 수집 순서로 진행합니다.

### 1단계 — Git 설치

코드를 내려받으려면 Git이 필요합니다.

**Windows**
- [Git for Windows 다운로드](https://git-scm.com/download/win) 후 설치
- 설치 중 모든 옵션은 기본값으로 진행해도 됩니다

**Mac**
- 터미널에서 `git --version` 입력 시 자동 설치 안내가 뜨거나, [Git 다운로드](https://git-scm.com/download/mac)

**Ubuntu (Linux)**
```bash
sudo apt install -y git
```

---

### 2단계 — Docker 설치 및 환경 설정

**Windows / Mac**
- [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop/) 후 설치
- 설치 완료 후 **Docker Desktop을 실행**합니다 (상단 바에 고래 아이콘이 뜨면 준비 완료)
- Docker Desktop이 실행된 상태여야 이후 명령어가 동작합니다

**Ubuntu (Linux)**
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker
```

설치 확인:
```bash
docker --version
docker compose version
```

두 명령어 모두 버전 번호가 출력되면 정상입니다.

---

#### Docker Desktop 리소스 설정 (Windows / Mac 필수)

이 프로젝트는 Selenium(Chrome) + MySQL + Next.js를 동시에 실행하므로,
Docker Desktop 기본 메모리(2GB)로는 크롤링 시 부족할 수 있습니다.

**Docker Desktop → Settings → Resources → Memory를 4GB 이상으로 설정**하세요.

```
Docker Desktop 상단 톱니바퀴(⚙) 아이콘 클릭
→ Resources
→ Memory 슬라이더를 4.00 GB 이상으로 조정
→ Apply & Restart
```

---

### 3단계 — 코드 내려받기

터미널(Windows: 명령 프롬프트 또는 PowerShell)을 열고 입력합니다:

```bash
git clone https://github.com/[계정명]/[레포명].git
cd project_card_recommend
```

`cd` 명령어 실행 후 터미널 경로가 `project_card_recommend`로 바뀌면 정상입니다.

---

### 4단계 — 환경변수 설정 (.env 파일 생성)

`.env` 파일은 **프로젝트 최상위 폴더**(docker-compose.yml이 있는 위치)에 있어야 합니다.

```
project_card_recommend/   ← 이 폴더 안에 .env 파일을 만듭니다
├── .env                  ← 여기!
├── .env.example          ← 이 파일을 복사해서 만듭니다
├── docker-compose.yml
├── backend/
├── frontend/
└── nginx/
```

**Mac / Linux:**
```bash
# .env.example을 복사해서 .env 파일 생성 후 편집기로 열기
cp .env.example .env
nano .env
```

**Windows:**
```
1. 탐색기에서 project_card_recommend 폴더 열기
2. .env.example 파일 선택 후 Ctrl+C (복사)
3. 같은 폴더에 Ctrl+V (붙여넣기)
4. 복사된 파일 이름을 ".env"로 변경
   → 이름 변경이 안 될 경우: ".env." (마지막에 점 추가)로 입력하면 자동으로 .env가 됩니다
5. 파일을 마우스 우클릭 → "메모장으로 열기"
```

파일 내용에서 비밀번호만 원하는 값으로 수정합니다:

```
MYSQL_ROOT_PASSWORD=원하는비밀번호   ← 이 부분만 수정 (영문+숫자 조합 권장)
DOMAIN_URL=http://localhost         ← 로컬 실행 시 수정하지 않아도 됩니다
```

저장합니다:
- nano: `Ctrl+O` → Enter → `Ctrl+X`
- 메모장: `Ctrl+S`

---

### 5단계 — Docker 컨테이너 빌드 및 실행

> Docker Desktop이 실행 중인지 먼저 확인하세요 (고래 아이콘 확인).

```bash
docker compose up --build
```

처음 실행 시 이미지 빌드 때문에 **5~10분** 정도 소요됩니다.
아래 메시지가 보이면 정상적으로 실행된 것입니다:

```
kb_backend   | INFO: Application startup complete.
kb_frontend  | ✓ Ready
```

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | http://localhost:3000 |
| 백엔드 API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |

---

### 6단계 — 카드 데이터 수집

서버가 실행된 상태에서 **새 터미널**을 열고 아래 명령어를 입력합니다:

```bash
curl -X POST http://localhost:8000/api/crawl/trigger
```

> `curl`이 없는 경우: 브라우저에서 `http://localhost:8000/docs` 접속 →
> `/api/crawl/trigger` 항목 클릭 → **Try it out** → **Execute** 버튼 클릭

수집 진행 상황 확인:
```bash
docker logs -f kb_backend
```

신용카드 105개, 체크카드 23개가 수집되면 완료입니다 (수분 소요).
로그 확인을 종료하려면 `Ctrl+C`를 누르세요.

이후 매주 월요일 00:00 KST에 자동으로 재수집됩니다.

---

### 7단계 — 서비스 사용

브라우저에서 `http://localhost:3000` 접속 후:
1. 카테고리별 월 지출 금액 입력
2. 카드 유형(전체 / 신용 / 체크), 추천 수 선택
3. **카드 추천받기** 버튼 클릭

---

### 자주 쓰는 명령어

```bash
# 컨테이너 중지
docker compose down

# 컨테이너 재시작 (코드 변경 없을 때)
docker compose up -d

# 백엔드 코드 변경 후 재시작 (자동 반영, 재빌드 불필요)
docker compose restart backend

# 프론트엔드 코드 변경 후 재빌드
docker compose up --build -d frontend

# 전체 로그 확인
docker compose logs -f

# 특정 서비스 로그 확인
docker logs -f kb_backend
docker logs -f kb_frontend
```

---

## 프로덕션 배포 (AWS EC2)

### 권장 인스턴스 사양

- **인스턴스**: t3.small 이상 (RAM 2GB + 스왑 2GB 권장)
- **OS**: Ubuntu 22.04 LTS
- **보안 그룹 인바운드**: 22(SSH), 80(HTTP) 허용

### 1단계 — EC2 초기 설정

SSH로 EC2에 접속 후 아래 명령어를 순서대로 실행합니다:

```bash
# Docker + Git 설치
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER && newgrp docker

# Docker buildx 최신 버전 설치 (빌드에 필요)
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/buildx/releases/download/v0.17.0/buildx-v0.17.0.linux-amd64 \
  -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx

# 스왑 메모리 추가 (t3.small RAM 2GB 보완 — Chrome 크롤링 시 메모리 부족 방지)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2단계 — 코드 내려받기

```bash
git clone https://github.com/[계정명]/[레포명].git
cd project_card_recommend
```

### 3단계 — 환경변수 설정

```bash
cp .env.example .env
nano .env
```

아래 내용을 수정합니다:
```
MYSQL_ROOT_PASSWORD=강한비밀번호      ← 영문+숫자+특수문자 조합 권장
DOMAIN_URL=http://[EC2-퍼블릭-IP]    ← AWS Console에서 확인한 퍼블릭 IPv4 주소
```

저장: `Ctrl+O` → Enter → `Ctrl+X`

### 4단계 — 빌드 및 실행

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

처음 빌드 시 **10~20분** 소요됩니다. 완료 후 확인:

```bash
docker compose ps
```

`kb_mysql`, `kb_backend`, `kb_frontend`, `kb_nginx` 모두 `Up` 상태이면 정상입니다.

### 5단계 — 초기 카드 데이터 수집

```bash
curl -X POST http://localhost:8000/api/crawl/trigger

# 진행 상황 확인
docker logs -f kb_backend
```

### 6단계 — 접속 확인

브라우저에서 `http://[EC2-퍼블릭-IP]` 접속

---

### 로컬 vs 프로덕션 비교

| 항목 | 로컬 | EC2 (prod) |
|------|------|------------|
| 접속 포트 | 3000(프론트), 8000(백엔드) | 80 단일 진입 |
| 백엔드 실행 | `--reload` (코드 변경 자동 반영) | workers 2 (안정적) |
| 코드 마운트 | 볼륨 마운트 (핫리로드) | 없음 (이미지 내장) |
| MySQL 포트 | 3307 외부 노출 | 컨테이너 내부만 |
| Nginx | 없음 | 추가 (리버스 프록시) |

### HTTPS 설정 (선택)

Let's Encrypt 인증서 발급 후 `nginx/nginx.conf`의 HTTPS 섹션 주석 해제:

```
./nginx/ssl/fullchain.pem
./nginx/ssl/privkey.pem
```

---

## 개발 현황

| 기능 | 상태 |
|------|------|
| KB카드 목록 크롤러 (Selenium, 전체 탭) | 완료 |
| KB카드 상세 크롤러 (requests + BS4) | 완료 |
| 전월실적 구간별 혜택 수집 (1/2/3구간) | 완료 |
| 혜택률 범위 수집 (rate_min / rate_max) | 완료 |
| 카드 이미지 URL 수집 (cooperation_code 패턴) | 완료 |
| MySQL 연동 | 완료 |
| 카드 목록/상세 API | 완료 |
| 규칙 기반 추천 엔진 | 완료 |
| 프론트엔드 UI (M3 디자인, KB 폰트) | 완료 |
| AWS EC2 배포 | 완료 |
| ML 기반 추천 엔진 | 개발 예정 |
| HTTPS 설정 | 선택 사항 |
