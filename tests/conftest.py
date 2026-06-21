"""Crawler 단위 테스트 conftest.

playwright 등 무거운 의존성이 로컬에 없어도 src 모듈을 임포트할 수 있도록
sys.modules에 stub을 삽입한다. pytest가 테스트 수집 전에 conftest를 먼저 실행하므로
개별 테스트 파일보다 먼저 적용된다.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock


def _stub(name: str) -> MagicMock:
    # spec 미지정: from module import Foo 형태의 임포트에서도 임의 속성 접근 허용
    mod = MagicMock()
    mod.__name__ = name
    mod.__spec__ = None
    mod.__path__ = []
    return mod


# playwright.sync_api — sync_playwright, Page 등 필요한 속성만 설정
if "playwright" not in sys.modules:
    pw_root = _stub("playwright")
    pw_sync = _stub("playwright.sync_api")
    pw_sync.sync_playwright = MagicMock()
    pw_sync.Page = MagicMock()
    pw_sync.Browser = MagicMock()
    pw_sync.BrowserContext = MagicMock()
    pw_root.sync_api = pw_sync
    sys.modules["playwright"] = pw_root
    sys.modules["playwright.sync_api"] = pw_sync

# 크롤러 모듈 중 playwright 의존성이나 Python 3.10+ 문법을 사용하는 모듈 stub 처리.
# ext_blog 단위 테스트는 NaverBlogLinkCrawler / stream_client만 사용하므로 안전하다.
for _crawler_mod in (
    "src.crawlers.assaview_crawler",
    "src.crawlers.assaview_detail_crawler",
    "src.crawlers.stylec_crawler",
    "src.crawlers.stylec_detail_crawler",
):
    if _crawler_mod not in sys.modules:
        sys.modules[_crawler_mod] = _stub(_crawler_mod)

# 크롤러 컨트롤러가 의존하는 비핵심 패키지/모듈 stub 처리
for _dep_mod in (
    "pandas",
    "src.repositories.campaign_repository",
    "src.views.cli_view",
):
    if _dep_mod not in sys.modules:
        stub = _stub(_dep_mod)
        # campaign_repository: save_campaigns_csv 함수 노출
        stub.save_campaigns_csv = MagicMock(return_value="output.csv")
        # cli_view: print_campaigns 함수 노출
        stub.print_campaigns = MagicMock()
        sys.modules[_dep_mod] = stub
