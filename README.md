# Blog Crawler

FastAPI 기반 크롤러 프로젝트입니다. 현재 두 가지 기능을 제공합니다.

- 체험단 캠페인 수집
- 네이버 블로그 목록 페이지에서 상세 페이지 링크 수집

## 요구 사항

- Python 3.11 이상
- Poetry
- Playwright Chromium

## 설치

```powershell
poetry install
poetry run playwright install chromium
```

## 실행

```powershell
poetry run python main.py
```

또는:

```powershell
poetry run uvicorn src.app:app --reload
```

## 문서 주소

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## API 예시

헬스 체크:

```http
GET /health
```

캠페인 단일 사이트 크롤링:

```http
POST /crawl/campain/assaview?save_csv=true
POST /crawl/campain/stylec?save_csv=true
```

캠페인 전체 크롤링:

```http
POST /crawl/campain?save_csv=true
```

네이버 블로그 상세 링크 수집:

```http
POST /crawl/blog/detail-links
Content-Type: application/json
```

요청 본문:

```json
{
  "url": "https://blog.naver.com/PostList.naver?blogId=cha_23&categoryNo=34&parentCategoryNo=34"
}
```

응답 예시:

```json
{
  "source_url": "https://blog.naver.com/PostList.naver?blogId=cha_23&categoryNo=34&parentCategoryNo=34",
  "resolved_list_url": "https://blog.naver.com/PostList.naver?blogId=cha_23&categoryNo=34&parentCategoryNo=34",
  "blog_id": "cha_23",
  "count": 16,
  "detail_urls": [
    "https://blog.naver.com/PostView.naver?blogId=cha_23&logNo=224265061522"
  ]
}
```

이 엔드포인트는 추출한 상세 링크를 응답으로 반환하고 서버 로그에도 순서대로 출력합니다.

## 출력 위치

- 원본 HTML: `data/raw`
- CSV 결과: `data/output`
