from pydantic import BaseModel
from urllib.parse import quote


class Settings(BaseModel):
    assaview_url: str = "https://assaview.co.kr/"
    stylec_base_url: str = "https://www.stylec.co.kr/index.php"
    stylec_count: int = 50
    stylec_pages: int = 5
    stylec_sns: str = quote("네이버블로그")

    headless: bool = True
    timeout_ms: int = 15000


settings = Settings()