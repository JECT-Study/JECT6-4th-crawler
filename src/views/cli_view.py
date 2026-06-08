from loguru import logger
from src.models.campaign import Campaign


def print_campaigns(campaigns: list[Campaign]) -> None:
    logger.info(f"총 {len(campaigns)}개 수집")
    for i, c in enumerate(campaigns, 1):
        logger.info(
            f"[{i}] {c.title} | "
            f"{c.type or '-'} | "
            f"{c.apply_end_date or '-'} | "
            f"신청 {c.apply_count or 0}/{c.recruit_count or 0}"
        )