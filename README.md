# JECT 6기 크롤러

리뷰노트, 구구다스, 네이버 블로그 글을 수집해 CSV로 저장하는 Python 프로젝트입니다.

## 실행 환경

- Python 3.11
- Poetry
- Playwright Chromium

## 설치

### 1. 의존성 설치

```bash
poetry install
```

### 2. Playwright 브라우저 설치

```bash
poetry run playwright install chromium
```

## 실행 방법

전체 실행:

```bash
poetry run python -m src.app
```

리뷰노트만 실행:

```bash
poetry run python -m src.app --site reviewnote
```

구구다스만 실행:

```bash
poetry run python -m src.app --site gugudas
```

네이버 블로그 글만 실행:

```bash
poetry run python -m src.app --site blog --url "https://blog.naver.com/PostView.naver?blogId=feb2nd&logNo=222953760599"
```

## 블로그 URL 입력 형식

아래 형식들을 모두 입력할 수 있습니다.

정식 URL:

```text
https://blog.naver.com/PostView.naver?blogId=feb2nd&logNo=222953760599
```

짧은 URL:

```text
https://blog.naver.com/belvisolibriinsight/224246481961
```

쿼리가 붙은 URL:

```text
https://blog.naver.com/de9508/224216304078?isInf=true&trackingCode=naver_etc
```

프로그램 내부에서 위 URL들을 자동으로 `PostView.naver?blogId=...&logNo=...` 형식으로 변환해 처리합니다.

## 결과물

CSV 결과 파일은 `data/output/` 아래 생성됩니다.

예시:

- `data/output/reviewnote_campaigns.csv`
- `data/output/gugudas_campaigns.csv`
- `data/output/blog_post_campaigns.csv`

## 설정

기본 설정은 [src/config/settings.py](/c:/Users/toki0/OneDrive/바탕%20화면/JECT/JECT6-4th-crawler/src/config/settings.py)에 있습니다.

- `reviewnote_url`: 리뷰노트 수집 URL
- `gugudas_url`: 구구다스 수집 URL
- `headless`: 브라우저 헤드리스 실행 여부
- `timeout_ms`: 페이지 로딩 타임아웃

현재 코드 기준으로 블로그 수집은 `--url` 인자를 넘겨 실행하는 방식을 사용합니다.

## 프로젝트 구조

```text
src/
  app.py
  controllers/
  crawlers/
  extractors/
  models/
  repositories/
  views/
```

## 참고

- `python src/app.py` 대신 `python -m src.app`으로 실행해야 import 경로가 올바르게 동작합니다.
- 블로그 수집은 중간 HTML을 `data/raw/`에 저장하지 않고 바로 결과만 출력합니다.
- 구구다스 크롤러는 실행 중 `data/raw/gugudas_debug.png` 스크린샷을 생성합니다.
