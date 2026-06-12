FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# poetry 없이 pip로 설치하기 위해 requirements 방식 사용
COPY pyproject.toml ./

RUN python3 -c \
    "import tomllib, subprocess, sys; \
    f=open('pyproject.toml','rb'); data=tomllib.load(f); f.close(); \
    deps=data.get('project',{}).get('dependencies',[]); \
    clean=[d.replace(' (','').replace(')','') for d in deps]; \
    subprocess.check_call([sys.executable,'-m','pip','install','--no-cache-dir']+clean)"

# Playwright 브라우저 설치
RUN playwright install chromium && playwright install-deps chromium

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
