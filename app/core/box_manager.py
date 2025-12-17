import asyncio
import random


class BoxManager:
    """Isolate box'larni boshqarish"""
    
    def __init__(self, min_id: int = 0, max_id: int = 999):
        self.min_id = min_id
        self.max_id = max_id
        self._used_boxes = set()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> int:
        """Bo'sh box_id olish"""
        async with self._lock:
            available = set(range(self.min_id, self.max_id + 1)) - self._used_boxes
            
            if not available:
                raise Exception("Barcha boxlar band! Iltimos biroz kuting.")
            
            box_id = random.choice(list(available))
            self._used_boxes.add(box_id)
            return box_id
    
    async def release(self, box_id: int):
        """Box'ni bo'shatish"""
        async with self._lock:
            self._used_boxes.discard(box_id)
