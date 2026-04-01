# EasyFin_mvp/frontend/Dockerfile
FROM nginx:alpine

# 기본 nginx html 폴더 비우고 index.html, styles.css 복사
RUN rm -rf /usr/share/nginx/html/*

COPY index.html /usr/share/nginx/html/index.html
COPY styles.css /usr/share/nginx/html/styles.css

# 포트 80으로 제공됨 (docker-compose에서 3000:80)
