# EasyFin_mvp/backend/Dockerfile
FROM python:3.10-slim

# 시스템 기본 설정 (선택사항)
ENV PYTHONUNBUFFERED=1

# 작업 디렉터리
WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
# (models, main.py 등 포함)
COPY . .

# Gunicorn + UvicornWorker 로 FastAPI 실행
#   - workers 1개로 고정 → DB DDL(create_all) 동시 실행 문제 방지
CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1"]
