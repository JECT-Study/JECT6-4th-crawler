from pydantic import BaseModel

class Settings(BaseModel):
    assaview_url: str = "https://assaview.co.kr/"
    stylec_url: str = (
        "https://www.stylec.co.kr/"
        "?sortOption=wr_last&pageNumber=1&count=50"
        "&campaignType=&category=&region=&sns=&include_finish=false"
    )
    headless: bool = True
    timeout_ms: int = 15000


settings = Settings()