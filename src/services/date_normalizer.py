from __future__ import annotations

import re
from datetime import date, timedelta


_DATE_WITH_YEAR_RE = re.compile(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})")
_DATE_WITHOUT_YEAR_RE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})(?!\d)")
_DAYS_LEFT_RE = re.compile(r"(\d+)\s*일\s*남음")
_D_DAY_RE = re.compile(r"d\s*-\s*(\d+)", re.IGNORECASE)


def normalize_spring_date(value: str | None, today: date | None = None) -> str | None:
    if value is None:
        return None

    base_date = today or date.today()
    text = str(value).strip()
    compact = re.sub(r"\s+", "", text)

    if not compact:
        return base_date.isoformat()

    if "오늘" in compact or compact in {"마감", "마감임박", "상시"}:
        return base_date.isoformat()

    if "내일" in compact:
        return (base_date + timedelta(days=1)).isoformat()

    days_left_match = _DAYS_LEFT_RE.search(text)
    if days_left_match:
        return (base_date + timedelta(days=int(days_left_match.group(1)))).isoformat()

    d_day_match = _D_DAY_RE.search(text)
    if d_day_match:
        return (base_date + timedelta(days=int(d_day_match.group(1)))).isoformat()

    date_with_year_match = _DATE_WITH_YEAR_RE.search(text)
    if date_with_year_match:
        normalized = _format_date(
            int(date_with_year_match.group(1)),
            int(date_with_year_match.group(2)),
            int(date_with_year_match.group(3)),
        )
        if normalized:
            return normalized

    date_without_year_match = _DATE_WITHOUT_YEAR_RE.search(text)
    if date_without_year_match:
        normalized = _format_date(
            base_date.year,
            int(date_without_year_match.group(1)),
            int(date_without_year_match.group(2)),
        )
        if normalized:
            return normalized

    return base_date.isoformat()


def _format_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None
