from pydantic import BaseModel


class Settings(BaseModel):
    assaview_url: str = "https://assaview.co.kr/"

    # index.php → / 로 변경, sns 파라미터 제거 (URL에서 직접 처리)
    stylec_base_url: str = "https://www.stylec.co.kr/"
    stylec_count: int = 50
    stylec_pages: int = 5

    headless: bool = True
    timeout_ms: int = 15000


settings = Settings()