from pydantic import BaseModel

class Settings(BaseModel):
    reviewnote_url: str = "https://www.reviewnote.co.kr/"
    gugudas_url: str = (
        "https://99das.com/amz/cmpn/amzCmpnList.do"
        "?cmpnDcd=AMZ027.002&searchCmpnDetlDcd=&sns=AMZ021.005&orderby=new"
    )
    headless: bool = False
    timeout_ms: int = 15000
    
settings = Settings()