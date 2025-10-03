# boc_manager
from typing import Any, Dict, Optional


class BoxIDManager:
    """Box ID larni boshqarish"""
    
    def __init__(self, max_boxes: int = 100):
        self.max_boxes = max_boxes
        self.available = set(range(max_boxes))
        self.in_use = set()
        self.stats = {
            'total_requests': 0,
            'successful_runs': 0,
            'failed_runs': 0
        }
    
    def acquire(self) -> Optional[int]:
        """Box ID olish"""
        if not self.available:
            return None
        box_id = self.available.pop()
        self.in_use.add(box_id)
        return box_id
    
    def release(self, box_id: int):
        """Box ID ni qaytarish"""
        if box_id in self.in_use:
            self.in_use.remove(box_id)
            self.available.add(box_id)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            'available_boxes': len(self.available),
            'in_use_boxes': len(self.in_use),
            'total_boxes': self.max_boxes
        }