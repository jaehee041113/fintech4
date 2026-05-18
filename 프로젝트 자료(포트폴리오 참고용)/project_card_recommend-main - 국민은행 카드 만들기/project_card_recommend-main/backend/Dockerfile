# ── Stage 1: 의존성 설치 ──────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Chromium 설치에 필요한 패키지
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: 런타임 ───────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Chromium + ChromeDriver 설치 (Selenium용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver \
    fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# Docker 환경에서 Chromium 경로 환경변수
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PYTHONUNBUFFERED=1

# builder에서 패키지 복사
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 소스 코드 복사
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
