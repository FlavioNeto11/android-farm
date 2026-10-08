import asyncio
import random
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class DelayConfig:
    between_actions: Tuple[float, float] = (3.0, 8.0)
    typing_char: Tuple[float, float] = (0.1, 0.3)
    typing_before: Tuple[float, float] = (0.5, 1.5)
    typing_after: Tuple[float, float] = (0.2, 0.6)
    mouse_before: Tuple[float, float] = (0.1, 0.3)
    mouse_step: Tuple[float, float] = (0.02, 0.08)
    scroll_after_down: Tuple[float, float] = (0.5, 1.5)
    scroll_after_up: Tuple[float, float] = (0.3, 0.8)
    warmup: Tuple[float, float] = (5.0, 10.0)
    
    @classmethod
    def conservative(cls):
        return cls(
            between_actions=(3.0, 8.0),
            typing_char=(0.1, 0.3),
            typing_before=(0.5, 1.5),
            warmup=(5.0, 10.0),
        )
    
    @classmethod
    def normal(cls):
        return cls(
            between_actions=(2.0, 4.0),
            typing_char=(0.05, 0.15),
            typing_before=(0.3, 0.8),
            warmup=(3.0, 5.0),
        )


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 720},
    {"width": 1600, "height": 900},
]


class HumanBehaviorSimulator:
    
    @staticmethod
    async def random_delay(min_sec: float = None, max_sec: float = None, config: DelayConfig = None):
        if config and min_sec is None:
            min_sec, max_sec = config.between_actions
        elif min_sec is None:
            min_sec, max_sec = 1.0, 3.0
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
    
    @staticmethod
    async def warmup_delay(config: DelayConfig = None):
        if config is None:
            config = DelayConfig.conservative()
        delay = random.uniform(*config.warmup)
        await asyncio.sleep(delay)
    
    @staticmethod
    async def type_like_human(page, selector: str, text: str, config: DelayConfig = None):
        if config is None:
            config = DelayConfig.conservative()
        
        locator = page.locator(selector).first
        if await locator.count() == 0:
            locator = page.locator("input:visible, textarea:visible").first
        
        await locator.click()
        await asyncio.sleep(random.uniform(*config.typing_before))
        
        for char in text:
            await page.keyboard.type(char, delay=random.uniform(*config.typing_char))
            
            if random.random() < 0.02:
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await page.keyboard.type(char, delay=random.uniform(*config.typing_char))
        
        await asyncio.sleep(random.uniform(*config.typing_after))
    
    @staticmethod
    async def move_mouse_human_like(page, target_selector: str):
        locator = page.locator(target_selector).first
        if await locator.count() == 0:
            return
        
        box = await locator.bounding_box()
        if not box:
            return
        
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        
        start_x, start_y = random.randint(100, 300), random.randint(100, 300)
        await page.mouse.move(start_x, start_y)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        steps = random.randint(5, 15)
        for i in range(1, steps + 1):
            progress = i / steps
            current_x = start_x + (target_x - start_x) * progress + random.uniform(-10, 10)
            current_y = start_y + (target_y - start_y) * progress + random.uniform(-10, 10)
            await page.mouse.move(current_x, current_y)
            await asyncio.sleep(random.uniform(0.02, 0.08))
    
    @staticmethod
    async def random_scroll(page):
        scroll_amount = random.randint(100, 500)
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.mouse.wheel(0, -scroll_amount // 2)
        await asyncio.sleep(random.uniform(0.3, 0.8))
    
    @staticmethod
    def get_random_user_agent() -> str:
        return random.choice(USER_AGENTS)
    
    @staticmethod
    def get_random_viewport() -> Dict[str, int]:
        return random.choice(VIEWPORTS)
