import asyncio

class BoxManager:
    def __init__(self, min_id=0, max_id=999):
        self.available_ids = asyncio.Queue()
        for i in range(min_id, max_id + 1):
            self.available_ids.put_nowait(i)

    async def acquire(self):
        return await self.available_ids.get()

    async def release(self, box_id):
        await self.available_ids.put(box_id)

box_manager = BoxManager()