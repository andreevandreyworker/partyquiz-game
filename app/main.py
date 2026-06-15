from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, engine
from app.exceptions import register_exception_handlers
from app.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="game-service", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
