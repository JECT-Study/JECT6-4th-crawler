FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# poetry 없이 pip로 설치하기 위해 requirements 방식 사용
COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir poetry==1.8.3 \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Playwright 브라우저 설치
RUN playwright install chromium && playwright install-deps chromium

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
