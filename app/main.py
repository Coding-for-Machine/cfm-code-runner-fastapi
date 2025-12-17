from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from api.run import api  # APIRouter import qilindi
from core.db import get_pool

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_pool()
    yield
    # Shutdown
    pool = await get_pool()
    await pool.close()

app.router.lifespan_context = lifespan  # lifespan context qo‘shish

# APIRouterni qo‘shish
app.include_router(api, prefix="/api")  # <-- include_router ishlatiladi

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
