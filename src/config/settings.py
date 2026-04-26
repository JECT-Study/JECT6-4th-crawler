from urllib.parse import quote

from pydantic import BaseModel


class Settings(BaseModel):
    assaview_url: str = "https://assaview.co.kr/"
    stylec_base_url: str = "https://www.stylec.co.kr/index.php"
    stylec_count: int = 50
    stylec_pages: int = 5
    stylec_sns: str = quote("네이버블로그")
    default_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    )
    request_delay_seconds: float = 0.8
    request_retry_count: int = 3
    request_backoff_seconds: float = 1.5
    headless: bool = True
    timeout_ms: int = 15000


settings = Settings()
