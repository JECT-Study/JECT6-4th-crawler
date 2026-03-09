from abc import ABC, abstractmethod
from src.models.campaign import Campaign


class BaseCrawler(ABC):
    @abstractmethod
    def crawl(self) -> list[Campaign]:
        raise NotImplementedError