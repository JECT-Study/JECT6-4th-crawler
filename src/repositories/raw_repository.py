from datetime import datetime
from pathlib import Path

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

def save_html(site_name: str, html: str) -> str:
    filename = f"{site_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path = RAW_DIR / filename
    path.write_text(html, encoding="utf-8")
    return str(path)