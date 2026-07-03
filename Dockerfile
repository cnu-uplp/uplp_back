FROM python:3.11-slim

WORKDIR /app

# 빌드 시 필요한 패키지 설치 및 요구사항 반영
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 소스 코드 전체 복사
COPY . .

# Render는 기본적으로 10000 포트를 사용하므로 맞춰줍니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]