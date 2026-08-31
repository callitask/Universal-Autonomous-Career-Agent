from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
import random

class JobBoardScraper(ABC):
    def __init__(self, ctx, page, browser):
        self.ctx = ctx
        self.page = page
        self.browser = browser
        self.logger = ctx.logger

    def random_sleep(self, min_s: float = 1.0, max_s: float = 3.0):
        time.sleep(random.uniform(min_s, max_s))

    @abstractmethod
    def scrape_jobs(self) -> List[Dict[str, Any]]:
        pass