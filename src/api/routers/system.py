from fastapi import APIRouter

from src.api.schemas import ServiceInfo
from src.api.site_registry import SUPPORTED_SITES

router = APIRouter(tags=["system"])


@router.get(
    "/",
    response_model=ServiceInfo,
    summary="서비스 정보 조회",
    description="현재 API 이름과 지원 중인 크롤링 도메인 목록을 반환합니다.",
)
def service_info() -> dict:
    return {
        "service": "blog-crawler",
        "supported_sites": [
            {
                "name": name,
                "domain": site["domain"],
                "description": site["description"],
            }
            for name, site in SUPPORTED_SITES.items()
        ],
    }


@router.get(
    "/health",
    summary="헬스 체크",
    description="현재 API 서버가 정상 동작 중인지 확인합니다.",
)
def health_check() -> dict:
    return {"status": "ok"}
