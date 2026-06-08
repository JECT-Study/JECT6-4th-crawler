SUPPORTED_SITES = {
    "assaview": {
        "domain": "https://assaview.co.kr",
        "description": "아싸뷰 체험단 캠페인 크롤러",
    },
    "stylec": {
        "domain": "https://www.stylec.co.kr",
        "description": "스타일C 체험단 캠페인 크롤러",
    },
    "naver-blog": {
        "domain": "https://blog.naver.com",
        "description": "네이버 블로그 목록 페이지 상세 링크 수집기",
    },
}

OPENAPI_TAGS = [
    {
        "name": "system",
        "description": "서비스 상태와 기본 메타데이터를 확인하는 엔드포인트입니다.",
    },
    {
        "name": "campaign",
        "description": "체험단 캠페인을 수집하는 엔드포인트입니다.",
    },
    {
        "name": "blog",
        "description": "네이버 블로그 목록 페이지에서 상세 페이지 링크를 수집하는 엔드포인트입니다.",
    },
]
