import asyncio
import random
from typing import Set


class BoxManager:
    """
    Isolate box'larni boshqarish uchun pool manager
    
    Box'lar 0-999 oralig'ida (1000 ta) parallel ishlashi mumkin
    """
    
    def __init__(self, min_id: int = 0, max_id: int = 999):
        self.min_id = min_id
        self.max_id = max_id
        self._used_boxes: Set[int] = set()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> int:
        """
        Bo'sh box_id olish
        
        Returns:
            int: Bo'sh box ID
        
        Raises:
            Exception: Agar barcha boxlar band bo'lsa
        """
        async with self._lock:
            available = set(range(self.min_id, self.max_id + 1)) - self._used_boxes
            
            if not available:
                raise Exception(
                    f"All {self.max_id - self.min_id + 1} boxes are in use. "
                    "Please wait and try again."
                )
            
            # Random box tanlash (load balancing uchun)
            box_id = random.choice(list(available))
            self._used_boxes.add(box_id)
            return box_id
    
    async def release(self, box_id: int):
        """
        Box'ni bo'shatish
        
        Args:
            box_id: Bo'shatilishi kerak bo'lgan box ID
        """
        async with self._lock:
            self._used_boxes.discard(box_id)
    
    def get_stats(self) -> dict:
        """
        Box'lar statistikasi
        
        Returns:
            dict: Total, used, available boxlar soni
        """
        total = self.max_id - self.min_id + 1
        used = len(self._used_boxes)
        return {
            "total": total,
            "used": used,
            "available": total - used,
            "usage_percent": round(used / total * 100, 2)
        }