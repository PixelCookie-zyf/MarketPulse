from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache import close_cache, init_cache
from app.config import settings
from app.routers import chart, commodities, indices, overview, sectors


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_cache()

    if settings.enable_scheduler:
        from app.scheduler import start_scheduler, stop_scheduler

        start_scheduler()
    else:
        stop_scheduler = None

    try:
        yield
    finally:
        if stop_scheduler is not None:
            stop_scheduler()
        await close_cache()


app = FastAPI(title="MarketPulse API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chart.router)
app.include_router(commodities.router)
app.include_router(indices.router)
app.include_router(sectors.router)
app.include_router(overview.router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "MarketPulse API",
        "status": "ok",
        "routes": ["/health", "/api/v1/overview"],
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/debug/global-indices")
async def debug_global_indices() -> dict:
    import traceback
    from app.fetchers.akshare_fetcher import AKShareFetcher
    try:
        fetcher = AKShareFetcher()
        result = await fetcher.fetch_global_indices()
        return {"ok": True, "us": len(result["us"]), "jp": len(result["jp"]), "kr": len(result["kr"]), "hk": len(result["hk"]), "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}
