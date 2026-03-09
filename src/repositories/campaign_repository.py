from pathlib import Path
import pandas as pd

from src.models.campaign import Campaign


OUTPUT_DIR = Path("data/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_campaigns_csv(filename: str, campaigns: list[Campaign]) -> str:
    df = pd.DataFrame([campaign.model_dump() for campaign in campaigns])
    path = OUTPUT_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)