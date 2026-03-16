# MarketPulse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-stack financial market monitoring app — Python FastAPI backend aggregating global market data, Swift iOS frontend with beautiful dashboard UI.

**Architecture:** FastAPI backend fetches data from AKShare (A股/港股), Alpha Vantage (美股/大宗商品), GoldAPI.io (贵金属) on schedule, caches in Redis, exposes REST API. Swift iOS app polls the backend and renders data in a 4-tab dashboard with dark/light theme support.

**Tech Stack:** Python 3.11+, FastAPI, AKShare, APScheduler, Redis (Upstash), Swift 5.9+, SwiftUI, Swift Charts, iOS 17+

**Data Sources (Updated after research):**
- A股指数 + 港股恒生: AKShare (`stock_zh_index_spot_em`, `stock_zh_index_spot_sina`)
- A股行业板块: AKShare (`stock_board_industry_name_em`)
- 美股指数 (纳斯达克/标普/道琼斯): Alpha Vantage Global Quote
- 日韩指数 (日经225/KOSPI): Alpha Vantage Global Quote
- 贵金属 (黄金/白银): GoldAPI.io
- 铜/原油: Alpha Vantage Commodity endpoint

---

## Phase 1: Project Skeleton & GitHub Setup

### Task 1: Initialize Git repo and project structure

**Files:**
- Create: `MarketPulse/.gitignore`
- Create: `MarketPulse/README.md`

**Step 1: Initialize git repo**

```bash
cd /Users/zyf/VibeCodes/MarketPulse
git init
```

**Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
.env
venv/
.venv/

# iOS
*.xcuserdata
DerivedData/
build/
*.ipa
*.dSYM.zip

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
```

**Step 3: Create README.md**

```markdown
# MarketPulse

全球金融市场实时监控面板 — iOS 原生应用 + Python 后端

## Features
- 大宗商品实时价格（黄金、白银、铜、原油）
- 全球主要指数（美股、日韩、港股、A股）
- A股行业板块涨跌排行
- 深色/浅色双主题

## Tech Stack
- **Backend:** Python, FastAPI, AKShare, Redis
- **iOS:** Swift, SwiftUI, Swift Charts
```

**Step 4: Create directory structure**

```bash
mkdir -p backend/app/{routers,fetchers}
mkdir -p backend/tests
mkdir -p ios/
```

**Step 5: Commit**

```bash
git add .gitignore README.md docs/ backend/ ios/
git commit -m "chore: init project structure with design docs"
```

---

## Phase 2: Backend — Core Infrastructure

### Task 2: Backend Python environment and FastAPI skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`

**Step 1: Create requirements.txt**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
akshare>=1.14.0
apscheduler==3.10.4
redis[hiredis]==5.2.1
httpx==0.28.1
pydantic==2.10.0
pydantic-settings==2.7.0
python-dotenv==1.0.1
```

**Step 2: Create config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    goldapi_key: str = ""
    alphavantage_key: str = ""
    cache_ttl_commodity: int = 60  # seconds
    cache_ttl_index: int = 60
    cache_ttl_sector: int = 180

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 3: Create main.py with lifespan**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init Redis + scheduler
    from app.cache import init_redis
    from app.scheduler import start_scheduler

    await init_redis()
    start_scheduler()
    yield
    # Shutdown
    from app.scheduler import stop_scheduler

    stop_scheduler()


app = FastAPI(title="MarketPulse API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 4: Set up venv and install deps**

```bash
cd /Users/zyf/VibeCodes/MarketPulse/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 5: Verify server starts**

```bash
cd /Users/zyf/VibeCodes/MarketPulse/backend
uvicorn app.main:app --reload --port 8000
# Expected: Uvicorn running on http://127.0.0.1:8000
# GET /health → {"status": "ok"}
```

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): add FastAPI skeleton with config and health endpoint"
```

---

### Task 3: Redis cache layer

**Files:**
- Create: `backend/app/cache.py`

**Step 1: Create cache.py**

```python
import json
from typing import Any

import redis.asyncio as redis

from app.config import settings

_redis: redis.Redis | None = None


async def init_redis():
    global _redis
    _redis = redis.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> redis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    return _redis


async def cache_set(key: str, data: Any, ttl: int = 60):
    r = get_redis()
    await r.set(key, json.dumps(data, ensure_ascii=False, default=str), ex=ttl)


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    return json.loads(raw)
```

**Step 2: Commit**

```bash
git add backend/app/cache.py
git commit -m "feat(backend): add Redis cache layer"
```

---

### Task 4: Pydantic data models

**Files:**
- Create: `backend/app/models.py`

**Step 1: Create models.py**

```python
from pydantic import BaseModel


class CommodityItem(BaseModel):
    symbol: str          # e.g. "XAU"
    name: str            # e.g. "黄金"
    name_en: str         # e.g. "Gold"
    price: float
    change: float
    change_pct: float
    high: float
    low: float
    unit: str            # e.g. "USD/oz"


class IndexItem(BaseModel):
    symbol: str          # e.g. "sh000001"
    name: str            # e.g. "上证指数"
    value: float
    change: float
    change_pct: float
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    sparkline: list[float] = []


class SectorItem(BaseModel):
    name: str            # e.g. "半导体"
    change_pct: float
    turnover: float | None = None   # 成交额
    leading_stock: str | None = None


class OverviewResponse(BaseModel):
    timestamp: str
    commodities: list[CommodityItem]
    indices: dict[str, list[IndexItem]]  # keys: "us", "jp", "kr", "hk", "cn"
    sectors: list[SectorItem]
```

**Step 2: Commit**

```bash
git add backend/app/models.py
git commit -m "feat(backend): add Pydantic data models"
```

---

## Phase 3: Backend — Data Fetchers

### Task 5: AKShare fetcher (A股指数 + 港股 + 行业板块)

**Files:**
- Create: `backend/app/fetchers/akshare_fetcher.py`

**Step 1: Create akshare_fetcher.py**

This is the most important fetcher — covers A股指数, 恒生指数, and 行业板块.

```python
import akshare as ak

from app.cache import cache_set
from app.config import settings

# A股四大指数 + 恒生指数的代码映射
CN_INDEX_CODES = {
    "sh000001": "上证指数",
    "sh000300": "沪深300",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000688": "科创50",
}


async def fetch_cn_indices():
    """Fetch A-share index data from Sina via AKShare."""
    try:
        df = ak.stock_zh_index_spot_sina()
        results = []
        for code, name in CN_INDEX_CODES.items():
            row = df[df["代码"] == code]
            if row.empty:
                continue
            r = row.iloc[0]
            results.append({
                "symbol": code,
                "name": name,
                "value": float(r.get("最新价", 0)),
                "change": float(r.get("涨跌额", 0) or 0),
                "change_pct": float(r.get("涨跌幅", 0) or 0),
                "high": float(r.get("最高", 0) or 0),
                "low": float(r.get("最低", 0) or 0),
                "volume": float(r.get("成交量", 0) or 0),
                "sparkline": [],
            })
        await cache_set("indices:cn", results, ttl=settings.cache_ttl_index)
        return results
    except Exception as e:
        print(f"[AKShare] fetch_cn_indices error: {e}")
        return []


async def fetch_hk_index():
    """Fetch Hang Seng Index."""
    try:
        df = ak.stock_zh_index_spot_sina()
        row = df[df["代码"] == "sh000300"]  # fallback approach
        # Use the international index approach
        # AKShare provides index_investing_global for international indices
        # For now, use the Sina global index list
        results = []
        # Hang Seng via stock_hk_index_spot_sina or similar
        try:
            hk_df = ak.stock_zh_index_spot_sina()
            hsi_row = hk_df[hk_df["名称"].str.contains("恒生", na=False)]
            if not hsi_row.empty:
                r = hsi_row.iloc[0]
                results.append({
                    "symbol": str(r.get("代码", "HSI")),
                    "name": "恒生指数",
                    "value": float(r.get("最新价", 0)),
                    "change": float(r.get("涨跌额", 0) or 0),
                    "change_pct": float(r.get("涨跌幅", 0) or 0),
                    "high": float(r.get("最高", 0) or 0),
                    "low": float(r.get("最低", 0) or 0),
                    "volume": float(r.get("成交量", 0) or 0),
                    "sparkline": [],
                })
        except Exception:
            pass
        await cache_set("indices:hk", results, ttl=settings.cache_ttl_index)
        return results
    except Exception as e:
        print(f"[AKShare] fetch_hk_index error: {e}")
        return []


async def fetch_cn_sectors():
    """Fetch A-share industry sector board data."""
    try:
        df = ak.stock_board_industry_name_em()
        results = []
        for _, row in df.iterrows():
            results.append({
                "name": str(row.get("板块名称", "")),
                "change_pct": float(row.get("涨跌幅", 0) or 0),
                "turnover": float(row.get("总市值", 0) or 0),
                "leading_stock": str(row.get("领涨股票", "") or ""),
            })
        # Sort by change_pct descending
        results.sort(key=lambda x: x["change_pct"], reverse=True)
        await cache_set("sectors:cn", results, ttl=settings.cache_ttl_sector)
        return results
    except Exception as e:
        print(f"[AKShare] fetch_cn_sectors error: {e}")
        return []
```

**Step 2: Verify AKShare works locally**

```bash
cd /Users/zyf/VibeCodes/MarketPulse/backend
source venv/bin/activate
python3 -c "import akshare as ak; print(ak.stock_zh_index_spot_sina().head(3))"
```

Expected: DataFrame with A-share index data printed.

**Step 3: Commit**

```bash
git add backend/app/fetchers/
git commit -m "feat(backend): add AKShare fetcher for A-share indices and sectors"
```

---

### Task 6: Alpha Vantage fetcher (美股指数 + 日韩指数 + 铜/原油)

**Files:**
- Create: `backend/app/fetchers/alphavantage_fetcher.py`

**Step 1: Create alphavantage_fetcher.py**

```python
import httpx

from app.cache import cache_set
from app.config import settings

BASE_URL = "https://www.alphavantage.co/query"

# US indices ETF proxies (Alpha Vantage uses ETFs for index tracking)
US_INDEX_SYMBOLS = {
    "SPY": {"name": "标普500", "symbol": "SPX"},
    "QQQ": {"name": "纳斯达克", "symbol": "IXIC"},
    "DIA": {"name": "道琼斯", "symbol": "DJI"},
}

# Japan & Korea index ETFs
JPKR_INDEX_SYMBOLS = {
    "EWJ": {"name": "日经225", "symbol": "N225"},
    "EWY": {"name": "韩国KOSPI", "symbol": "KOSPI"},
}

COMMODITY_FUNCTIONS = {
    "WTI": {"function": "WTI", "name": "原油(WTI)", "name_en": "Crude Oil", "unit": "USD/bbl"},
    "COPPER": {"function": "COPPER", "name": "铜", "name_en": "Copper", "unit": "USD/lb"},
}


async def _fetch_global_quote(symbol: str) -> dict | None:
    """Fetch a single stock/ETF quote from Alpha Vantage."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(BASE_URL, params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": settings.alphavantage_key,
            })
            data = resp.json()
            quote = data.get("Global Quote", {})
            if not quote:
                return None
            return {
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_pct": float(quote.get("10. change percent", "0").replace("%", "")),
                "high": float(quote.get("03. high", 0)),
                "low": float(quote.get("04. low", 0)),
                "volume": float(quote.get("06. volume", 0)),
            }
    except Exception as e:
        print(f"[AlphaVantage] quote error for {symbol}: {e}")
        return None


async def fetch_us_indices():
    """Fetch US index data via ETF proxies."""
    results = []
    for etf_symbol, info in US_INDEX_SYMBOLS.items():
        quote = await _fetch_global_quote(etf_symbol)
        if quote:
            results.append({
                "symbol": info["symbol"],
                "name": info["name"],
                "value": quote["price"],
                "change": quote["change"],
                "change_pct": quote["change_pct"],
                "high": quote["high"],
                "low": quote["low"],
                "volume": quote["volume"],
                "sparkline": [],
            })
    await cache_set("indices:us", results, ttl=settings.cache_ttl_index)
    return results


async def fetch_jpkr_indices():
    """Fetch Japan and Korea index data via ETF proxies."""
    jp_results = []
    kr_results = []
    for etf_symbol, info in JPKR_INDEX_SYMBOLS.items():
        quote = await _fetch_global_quote(etf_symbol)
        if quote:
            item = {
                "symbol": info["symbol"],
                "name": info["name"],
                "value": quote["price"],
                "change": quote["change"],
                "change_pct": quote["change_pct"],
                "high": quote["high"],
                "low": quote["low"],
                "volume": quote["volume"],
                "sparkline": [],
            }
            if "日" in info["name"]:
                jp_results.append(item)
            else:
                kr_results.append(item)
    await cache_set("indices:jp", jp_results, ttl=settings.cache_ttl_index * 5)
    await cache_set("indices:kr", kr_results, ttl=settings.cache_ttl_index * 5)
    return jp_results, kr_results


async def fetch_commodities_av():
    """Fetch copper and oil prices from Alpha Vantage commodity endpoints."""
    results = []
    for key, info in COMMODITY_FUNCTIONS.items():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(BASE_URL, params={
                    "function": info["function"],
                    "interval": "daily",
                    "apikey": settings.alphavantage_key,
                })
                data = resp.json()
                # Alpha Vantage commodity returns "data" array
                entries = data.get("data", [])
                if entries:
                    latest = entries[0]
                    price = float(latest.get("value", 0))
                    # Calculate change from previous day
                    prev_price = float(entries[1].get("value", price)) if len(entries) > 1 else price
                    change = price - prev_price
                    change_pct = (change / prev_price * 100) if prev_price else 0
                    results.append({
                        "symbol": key,
                        "name": info["name"],
                        "name_en": info["name_en"],
                        "price": price,
                        "change": round(change, 4),
                        "change_pct": round(change_pct, 2),
                        "high": price,
                        "low": price,
                        "unit": info["unit"],
                    })
        except Exception as e:
            print(f"[AlphaVantage] commodity error for {key}: {e}")
    return results
```

**Step 2: Commit**

```bash
git add backend/app/fetchers/alphavantage_fetcher.py
git commit -m "feat(backend): add Alpha Vantage fetcher for US/JP/KR indices and commodities"
```

---

### Task 7: GoldAPI fetcher (黄金/白银)

**Files:**
- Create: `backend/app/fetchers/goldapi_fetcher.py`

**Step 1: Create goldapi_fetcher.py**

```python
import httpx

from app.cache import cache_set
from app.config import settings

BASE_URL = "https://www.goldapi.io/api"

METALS = {
    "XAU": {"name": "黄金", "name_en": "Gold", "unit": "USD/oz"},
    "XAG": {"name": "白银", "name_en": "Silver", "unit": "USD/oz"},
}


async def fetch_precious_metals():
    """Fetch gold and silver prices from GoldAPI.io."""
    results = []
    for symbol, info in METALS.items():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BASE_URL}/{symbol}/USD",
                    headers={"x-access-token": settings.goldapi_key},
                )
                data = resp.json()
                results.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "name_en": info["name_en"],
                    "price": float(data.get("price", 0)),
                    "change": float(data.get("ch", 0)),
                    "change_pct": float(data.get("chp", 0)),
                    "high": float(data.get("high_price", 0) or data.get("price", 0)),
                    "low": float(data.get("low_price", 0) or data.get("price", 0)),
                    "unit": info["unit"],
                })
        except Exception as e:
            print(f"[GoldAPI] error for {symbol}: {e}")
    await cache_set("commodities:metals", results, ttl=settings.cache_ttl_commodity)
    return results
```

**Step 2: Commit**

```bash
git add backend/app/fetchers/goldapi_fetcher.py
git commit -m "feat(backend): add GoldAPI fetcher for gold and silver prices"
```

---

## Phase 4: Backend — Scheduler & API Routes

### Task 8: APScheduler setup

**Files:**
- Create: `backend/app/scheduler.py`

**Step 1: Create scheduler.py**

```python
import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from app.fetchers.akshare_fetcher import fetch_cn_indices, fetch_hk_index, fetch_cn_sectors
from app.fetchers.alphavantage_fetcher import fetch_us_indices, fetch_jpkr_indices, fetch_commodities_av
from app.fetchers.goldapi_fetcher import fetch_precious_metals

_scheduler: BackgroundScheduler | None = None


def _run_async(coro):
    """Run async function from sync scheduler context."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def _fetch_cn_data():
    _run_async(fetch_cn_indices())
    _run_async(fetch_hk_index())


def _fetch_cn_sectors_job():
    _run_async(fetch_cn_sectors())


def _fetch_global_indices():
    _run_async(fetch_us_indices())
    _run_async(fetch_jpkr_indices())


def _fetch_commodities():
    _run_async(fetch_precious_metals())
    _run_async(fetch_commodities_av())


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()

    # A-share indices + HK: every 1 minute
    _scheduler.add_job(_fetch_cn_data, "interval", minutes=1, id="cn_indices")

    # A-share sectors: every 3 minutes
    _scheduler.add_job(_fetch_cn_sectors_job, "interval", minutes=3, id="cn_sectors")

    # Global indices: every 3 minutes (Alpha Vantage rate limit: 25/day free)
    _scheduler.add_job(_fetch_global_indices, "interval", minutes=3, id="global_indices")

    # Commodities: every 3 minutes
    _scheduler.add_job(_fetch_commodities, "interval", minutes=3, id="commodities")

    _scheduler.start()

    # Run all jobs once immediately at startup
    _fetch_cn_data()
    _fetch_cn_sectors_job()
    _fetch_global_indices()
    _fetch_commodities()


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
```

**Step 2: Commit**

```bash
git add backend/app/scheduler.py
git commit -m "feat(backend): add APScheduler with data fetch jobs"
```

---

### Task 9: API routes

**Files:**
- Create: `backend/app/routers/commodities.py`
- Create: `backend/app/routers/indices.py`
- Create: `backend/app/routers/sectors.py`
- Create: `backend/app/routers/overview.py`
- Modify: `backend/app/main.py` — register routers

**Step 1: Create commodities.py**

```python
from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get

router = APIRouter(prefix="/api/v1", tags=["commodities"])


@router.get("/commodities")
async def get_commodities():
    metals = await cache_get("commodities:metals") or []
    # Merge with copper/oil from Alpha Vantage
    # (stored separately by the AV fetcher — we combine here)
    av_commodities = await cache_get("commodities:av") or []
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": metals + av_commodities,
    }
```

**Step 2: Create indices.py**

```python
from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get

router = APIRouter(prefix="/api/v1", tags=["indices"])


@router.get("/indices/global")
async def get_global_indices():
    us = await cache_get("indices:us") or []
    jp = await cache_get("indices:jp") or []
    kr = await cache_get("indices:kr") or []
    hk = await cache_get("indices:hk") or []
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"us": us, "jp": jp, "kr": kr, "hk": hk},
    }


@router.get("/indices/cn")
async def get_cn_indices():
    cn = await cache_get("indices:cn") or []
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": cn,
    }
```

**Step 3: Create sectors.py**

```python
from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get

router = APIRouter(prefix="/api/v1", tags=["sectors"])


@router.get("/sectors/cn")
async def get_cn_sectors():
    sectors = await cache_get("sectors:cn") or []
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": sectors,
    }
```

**Step 4: Create overview.py**

```python
from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get

router = APIRouter(prefix="/api/v1", tags=["overview"])


@router.get("/overview")
async def get_overview():
    metals = await cache_get("commodities:metals") or []
    av_commodities = await cache_get("commodities:av") or []
    us = await cache_get("indices:us") or []
    jp = await cache_get("indices:jp") or []
    kr = await cache_get("indices:kr") or []
    hk = await cache_get("indices:hk") or []
    cn = await cache_get("indices:cn") or []
    sectors = await cache_get("sectors:cn") or []

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commodities": metals + av_commodities,
        "indices": {"us": us, "jp": jp, "kr": kr, "hk": hk, "cn": cn},
        "sectors": sectors,
    }
```

**Step 5: Update main.py to register routers**

Add after `app.add_middleware(...)`:

```python
from app.routers import commodities, indices, sectors, overview

app.include_router(commodities.router)
app.include_router(indices.router)
app.include_router(sectors.router)
app.include_router(overview.router)
```

**Step 6: Create `backend/app/routers/__init__.py`** and `backend/app/fetchers/__init__.py`

Empty `__init__.py` files for Python packages.

**Step 7: Verify all endpoints**

```bash
cd /Users/zyf/VibeCodes/MarketPulse/backend
uvicorn app.main:app --reload --port 8000
# Test: curl http://localhost:8000/api/v1/overview
# Test: curl http://localhost:8000/docs  (Swagger UI)
```

**Step 8: Commit**

```bash
git add backend/app/routers/ backend/app/main.py
git commit -m "feat(backend): add API routes for commodities, indices, sectors, and overview"
```

---

### Task 10: Fix Alpha Vantage commodity caching

**Files:**
- Modify: `backend/app/fetchers/alphavantage_fetcher.py`

**Step 1: Add cache_set call for AV commodities**

At the end of `fetch_commodities_av()`, before `return results`, add:

```python
    await cache_set("commodities:av", results, ttl=settings.cache_ttl_commodity)
```

**Step 2: Commit**

```bash
git add backend/app/fetchers/alphavantage_fetcher.py
git commit -m "fix(backend): cache Alpha Vantage commodity results"
```

---

### Task 11: Dockerfile for backend

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Create .env.example**

```env
REDIS_URL=redis://localhost:6379
GOLDAPI_KEY=your_goldapi_key_here
ALPHAVANTAGE_KEY=your_alphavantage_key_here
```

**Step 3: Commit**

```bash
git add backend/Dockerfile backend/.env.example
git commit -m "feat(backend): add Dockerfile and env example"
```

---

## Phase 5: iOS App — Project Setup & Models

### Task 12: Create Xcode project

**Step 1: Create iOS project via Xcode CLI or manually**

```bash
cd /Users/zyf/VibeCodes/MarketPulse/ios
```

Create a new SwiftUI App project named "MarketPulse" targeting iOS 17+.
Use Xcode → File → New → Project → App → SwiftUI → MarketPulse.
Save in `/Users/zyf/VibeCodes/MarketPulse/ios/`.

**Step 2: Commit**

```bash
git add ios/
git commit -m "feat(ios): init Xcode project"
```

---

### Task 13: iOS data models

**Files:**
- Create: `ios/MarketPulse/Models/MarketModels.swift`

**Step 1: Create MarketModels.swift**

```swift
import Foundation

// MARK: - API Response
struct OverviewResponse: Codable {
    let timestamp: String
    let commodities: [CommodityItem]
    let indices: IndexGroups
    let sectors: [SectorItem]
}

// MARK: - Commodity
struct CommodityItem: Codable, Identifiable {
    var id: String { symbol }
    let symbol: String
    let name: String
    let nameEn: String
    let price: Double
    let change: Double
    let changePct: Double
    let high: Double
    let low: Double
    let unit: String

    enum CodingKeys: String, CodingKey {
        case symbol, name, price, change, high, low, unit
        case nameEn = "name_en"
        case changePct = "change_pct"
    }

    var isUp: Bool { change >= 0 }
}

// MARK: - Index
struct IndexItem: Codable, Identifiable {
    var id: String { symbol }
    let symbol: String
    let name: String
    let value: Double
    let change: Double
    let changePct: Double
    let high: Double?
    let low: Double?
    let volume: Double?
    let sparkline: [Double]

    enum CodingKeys: String, CodingKey {
        case symbol, name, value, change, high, low, volume, sparkline
        case changePct = "change_pct"
    }

    var isUp: Bool { change >= 0 }
}

struct IndexGroups: Codable {
    let us: [IndexItem]
    let jp: [IndexItem]
    let kr: [IndexItem]
    let hk: [IndexItem]
    let cn: [IndexItem]
}

// MARK: - Sector
struct SectorItem: Codable, Identifiable {
    var id: String { name }
    let name: String
    let changePct: Double
    let turnover: Double?
    let leadingStock: String?

    enum CodingKeys: String, CodingKey {
        case name, turnover
        case changePct = "change_pct"
        case leadingStock = "leading_stock"
    }

    var isUp: Bool { changePct >= 0 }
}
```

**Step 2: Commit**

```bash
git add ios/MarketPulse/Models/
git commit -m "feat(ios): add Codable data models"
```

---

### Task 14: API service layer

**Files:**
- Create: `ios/MarketPulse/Services/APIService.swift`

**Step 1: Create APIService.swift**

```swift
import Foundation

actor APIService {
    static let shared = APIService()

    #if DEBUG
    private let baseURL = "http://localhost:8000/api/v1"
    #else
    private let baseURL = "https://your-backend.railway.app/api/v1"
    #endif

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        return d
    }()

    func fetchOverview() async throws -> OverviewResponse {
        let url = URL(string: "\(baseURL)/overview")!
        let (data, _) = try await URLSession.shared.data(from: url)
        return try decoder.decode(OverviewResponse.self, from: data)
    }

    func fetchCommodities() async throws -> [CommodityItem] {
        let url = URL(string: "\(baseURL)/commodities")!
        let (data, _) = try await URLSession.shared.data(from: url)
        struct Resp: Codable { let data: [CommodityItem] }
        return try decoder.decode(Resp.self, from: data).data
    }

    func fetchGlobalIndices() async throws -> IndexGroups {
        let url = URL(string: "\(baseURL)/indices/global")!
        let (data, _) = try await URLSession.shared.data(from: url)
        struct Resp: Codable { let data: IndexGroups }
        return try decoder.decode(Resp.self, from: data).data
    }

    func fetchCNIndices() async throws -> [IndexItem] {
        let url = URL(string: "\(baseURL)/indices/cn")!
        let (data, _) = try await URLSession.shared.data(from: url)
        struct Resp: Codable { let data: [IndexItem] }
        return try decoder.decode(Resp.self, from: data).data
    }

    func fetchSectors() async throws -> [SectorItem] {
        let url = URL(string: "\(baseURL)/sectors/cn")!
        let (data, _) = try await URLSession.shared.data(from: url)
        struct Resp: Codable { let data: [SectorItem] }
        return try decoder.decode(Resp.self, from: data).data
    }
}
```

**Step 2: Commit**

```bash
git add ios/MarketPulse/Services/
git commit -m "feat(ios): add API service layer"
```

---

## Phase 6: iOS App — Theme System

### Task 15: Theme and color system

**Files:**
- Create: `ios/MarketPulse/Theme/AppTheme.swift`

**Step 1: Create AppTheme.swift**

```swift
import SwiftUI

struct AppTheme {
    // MARK: - Colors
    struct Colors {
        static let background = Color("Background")
        static let cardBackground = Color("CardBackground")
        static let primaryText = Color("PrimaryText")
        static let secondaryText = Color("SecondaryText")

        static func changeColor(isUp: Bool) -> Color {
            isUp ? Color("UpColor") : Color("DownColor")
        }
    }

    // MARK: - Card Style
    struct CardStyle: ViewModifier {
        @Environment(\.colorScheme) var colorScheme

        func body(content: Content) -> some View {
            content
                .padding(16)
                .background(Colors.cardBackground)
                .cornerRadius(16)
                .shadow(
                    color: colorScheme == .dark
                        ? Color.clear
                        : Color.black.opacity(0.06),
                    radius: 8, x: 0, y: 2
                )
        }
    }
}

extension View {
    func cardStyle() -> some View {
        modifier(AppTheme.CardStyle())
    }
}
```

**Step 2: Add color assets in Assets.xcassets**

Create color sets for: `Background`, `CardBackground`, `PrimaryText`, `SecondaryText`, `UpColor`, `DownColor`.

| Color Name | Light | Dark |
|-----------|-------|------|
| Background | #F5F7FA | #0A0E17 |
| CardBackground | #FFFFFF | #151B28 |
| PrimaryText | #1A1A1A | #E0E0E0 |
| SecondaryText | #9CA3AF | #6B7280 |
| UpColor | #4CAF50 | #00E676 |
| DownColor | #F44336 | #FF1744 |

**Step 3: Commit**

```bash
git add ios/MarketPulse/Theme/
git commit -m "feat(ios): add theme system with dark/light color support"
```

---

## Phase 7: iOS App — ViewModels

### Task 16: Main ViewModel

**Files:**
- Create: `ios/MarketPulse/ViewModels/MarketViewModel.swift`

**Step 1: Create MarketViewModel.swift**

```swift
import Foundation
import Combine

@MainActor
class MarketViewModel: ObservableObject {
    @Published var commodities: [CommodityItem] = []
    @Published var indices: IndexGroups = IndexGroups(us: [], jp: [], kr: [], hk: [], cn: [])
    @Published var sectors: [SectorItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var lastUpdated: Date?

    private var refreshTimer: Timer?

    func startAutoRefresh(interval: TimeInterval = 60) {
        loadData()
        refreshTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.loadData()
            }
        }
    }

    func stopAutoRefresh() {
        refreshTimer?.invalidate()
        refreshTimer = nil
    }

    func loadData() {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil

        Task {
            do {
                let response = try await APIService.shared.fetchOverview()
                self.commodities = response.commodities
                self.indices = response.indices
                self.sectors = response.sectors
                self.lastUpdated = Date()
            } catch {
                self.errorMessage = error.localizedDescription
            }
            self.isLoading = false
        }
    }
}
```

**Step 2: Commit**

```bash
git add ios/MarketPulse/ViewModels/
git commit -m "feat(ios): add MarketViewModel with auto-refresh"
```

---

## Phase 8: iOS App — Views

### Task 17: App entry point and tab navigation

**Files:**
- Modify: `ios/MarketPulse/MarketPulseApp.swift`
- Create: `ios/MarketPulse/Views/ContentView.swift`

**Step 1: Update MarketPulseApp.swift**

```swift
import SwiftUI

@main
struct MarketPulseApp: App {
    @StateObject private var viewModel = MarketViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
        }
    }
}
```

**Step 2: Create ContentView.swift**

```swift
import SwiftUI

struct ContentView: View {
    @EnvironmentObject var viewModel: MarketViewModel

    var body: some View {
        TabView {
            OverviewView()
                .tabItem {
                    Label("总览", systemImage: "chart.bar.doc.horizontal")
                }

            CommodityListView()
                .tabItem {
                    Label("商品", systemImage: "cube.box")
                }

            IndicesView()
                .tabItem {
                    Label("指数", systemImage: "chart.line.uptrend.xyaxis")
                }

            SectorsListView()
                .tabItem {
                    Label("板块", systemImage: "square.grid.2x2")
                }
        }
        .onAppear {
            viewModel.startAutoRefresh()
        }
        .onDisappear {
            viewModel.stopAutoRefresh()
        }
    }
}
```

**Step 3: Commit**

```bash
git add ios/MarketPulse/
git commit -m "feat(ios): add tab navigation with 4 tabs"
```

---

### Task 18: Shared UI components

**Files:**
- Create: `ios/MarketPulse/Components/SparklineView.swift`
- Create: `ios/MarketPulse/Components/ChangeLabel.swift`

**Step 1: Create SparklineView.swift**

```swift
import SwiftUI
import Charts

struct SparklineView: View {
    let data: [Double]
    let isUp: Bool

    var body: some View {
        if data.isEmpty {
            Rectangle()
                .fill(Color.clear)
                .frame(height: 30)
        } else {
            Chart {
                ForEach(Array(data.enumerated()), id: \.offset) { index, value in
                    LineMark(
                        x: .value("Time", index),
                        y: .value("Value", value)
                    )
                    .foregroundStyle(AppTheme.Colors.changeColor(isUp: isUp))
                    .interpolationMethod(.catmullRom)
                }
            }
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .chartLegend(.hidden)
            .frame(height: 30)
        }
    }
}
```

**Step 2: Create ChangeLabel.swift**

```swift
import SwiftUI

struct ChangeLabel: View {
    let change: Double
    let changePct: Double
    let showValue: Bool

    init(change: Double, changePct: Double, showValue: Bool = true) {
        self.change = change
        self.changePct = changePct
        self.showValue = showValue
    }

    var isUp: Bool { change >= 0 }
    var arrow: String { isUp ? "▲" : "▼" }

    var body: some View {
        HStack(spacing: 4) {
            if showValue {
                Text("\(arrow) \(String(format: "%.2f", abs(change)))")
                    .font(.caption)
            }
            Text("(\(String(format: "%+.2f", changePct))%)")
                .font(.caption)
                .fontWeight(.medium)
        }
        .foregroundColor(AppTheme.Colors.changeColor(isUp: isUp))
    }
}
```

**Step 3: Commit**

```bash
git add ios/MarketPulse/Components/
git commit -m "feat(ios): add SparklineView and ChangeLabel components"
```

---

### Task 19: Overview tab

**Files:**
- Create: `ios/MarketPulse/Views/Overview/OverviewView.swift`
- Create: `ios/MarketPulse/Views/Overview/CommodityCardView.swift`
- Create: `ios/MarketPulse/Views/Overview/IndexRowView.swift`

**Step 1: Create CommodityCardView.swift**

```swift
import SwiftUI

struct CommodityCardView: View {
    let item: CommodityItem

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(item.name)
                    .font(.caption)
                    .foregroundColor(AppTheme.Colors.secondaryText)
                Spacer()
                Text(item.nameEn)
                    .font(.caption2)
                    .foregroundColor(AppTheme.Colors.secondaryText)
            }

            Text(String(format: "%.2f", item.price))
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(AppTheme.Colors.primaryText)

            ChangeLabel(change: item.change, changePct: item.changePct)

            Text(item.unit)
                .font(.caption2)
                .foregroundColor(AppTheme.Colors.secondaryText)
        }
        .cardStyle()
    }
}
```

**Step 2: Create IndexRowView.swift**

```swift
import SwiftUI

struct IndexRowView: View {
    let item: IndexItem

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(item.name)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(AppTheme.Colors.primaryText)
                Text(item.symbol)
                    .font(.caption2)
                    .foregroundColor(AppTheme.Colors.secondaryText)
            }

            Spacer()

            SparklineView(data: item.sparkline, isUp: item.isUp)
                .frame(width: 60)

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(String(format: "%.2f", item.value))
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppTheme.Colors.primaryText)
                ChangeLabel(change: item.change, changePct: item.changePct, showValue: false)
            }
        }
        .padding(.vertical, 8)
    }
}
```

**Step 3: Create OverviewView.swift**

```swift
import SwiftUI

struct OverviewView: View {
    @EnvironmentObject var viewModel: MarketViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Commodities grid
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                    ], spacing: 12) {
                        ForEach(viewModel.commodities) { item in
                            CommodityCardView(item: item)
                        }
                    }

                    // Global indices sections
                    indexSection(title: "🇺🇸 美股", items: viewModel.indices.us)
                    indexSection(title: "🇯🇵 日本", items: viewModel.indices.jp)
                    indexSection(title: "🇰🇷 韩国", items: viewModel.indices.kr)
                    indexSection(title: "🇭🇰 香港", items: viewModel.indices.hk)
                    indexSection(title: "🇨🇳 A股", items: viewModel.indices.cn)

                    // Sectors top 10
                    sectorSection()
                }
                .padding()
            }
            .background(AppTheme.Colors.background)
            .navigationTitle("MarketPulse")
            .refreshable {
                viewModel.loadData()
            }
        }
    }

    @ViewBuilder
    private func indexSection(title: String, items: [IndexItem]) -> some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.headline)
                    .foregroundColor(AppTheme.Colors.primaryText)

                VStack(spacing: 0) {
                    ForEach(items) { item in
                        IndexRowView(item: item)
                        if item.id != items.last?.id {
                            Divider()
                        }
                    }
                }
                .cardStyle()
            }
        }
    }

    private func sectorSection() -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("A股板块 TOP 10")
                .font(.headline)
                .foregroundColor(AppTheme.Colors.primaryText)

            VStack(spacing: 0) {
                ForEach(Array(viewModel.sectors.prefix(10))) { sector in
                    HStack {
                        Text(sector.name)
                            .font(.subheadline)
                            .foregroundColor(AppTheme.Colors.primaryText)
                        Spacer()
                        if let stock = sector.leadingStock, !stock.isEmpty {
                            Text(stock)
                                .font(.caption)
                                .foregroundColor(AppTheme.Colors.secondaryText)
                        }
                        Text(String(format: "%+.2f%%", sector.changePct))
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(AppTheme.Colors.changeColor(isUp: sector.isUp))
                            .frame(width: 70, alignment: .trailing)
                    }
                    .padding(.vertical, 8)

                    if sector.id != viewModel.sectors.prefix(10).last?.id {
                        Divider()
                    }
                }
            }
            .cardStyle()
        }
    }
}
```

**Step 4: Commit**

```bash
git add ios/MarketPulse/Views/Overview/
git commit -m "feat(ios): add Overview tab with commodity cards, index rows, and sector preview"
```

---

### Task 20: Commodity detail tab

**Files:**
- Create: `ios/MarketPulse/Views/Commodity/CommodityListView.swift`

**Step 1: Create CommodityListView.swift**

```swift
import SwiftUI

struct CommodityListView: View {
    @EnvironmentObject var viewModel: MarketViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    ForEach(viewModel.commodities) { item in
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(item.name)
                                        .font(.title3)
                                        .fontWeight(.bold)
                                        .foregroundColor(AppTheme.Colors.primaryText)
                                    Text(item.nameEn)
                                        .font(.caption)
                                        .foregroundColor(AppTheme.Colors.secondaryText)
                                }
                                Spacer()
                                VStack(alignment: .trailing, spacing: 4) {
                                    Text(String(format: "%.2f", item.price))
                                        .font(.title2)
                                        .fontWeight(.bold)
                                        .foregroundColor(AppTheme.Colors.primaryText)
                                    ChangeLabel(change: item.change, changePct: item.changePct)
                                }
                            }

                            Divider()

                            HStack {
                                statItem(label: "最高", value: String(format: "%.2f", item.high))
                                Spacer()
                                statItem(label: "最低", value: String(format: "%.2f", item.low))
                                Spacer()
                                statItem(label: "单位", value: item.unit)
                            }
                        }
                        .cardStyle()
                    }
                }
                .padding()
            }
            .background(AppTheme.Colors.background)
            .navigationTitle("大宗商品")
        }
    }

    private func statItem(label: String, value: String) -> some View {
        VStack(spacing: 4) {
            Text(label)
                .font(.caption)
                .foregroundColor(AppTheme.Colors.secondaryText)
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundColor(AppTheme.Colors.primaryText)
        }
    }
}
```

**Step 2: Commit**

```bash
git add ios/MarketPulse/Views/Commodity/
git commit -m "feat(ios): add Commodity list tab"
```

---

### Task 21: Indices tab

**Files:**
- Create: `ios/MarketPulse/Views/Indices/IndicesView.swift`

**Step 1: Create IndicesView.swift**

```swift
import SwiftUI

struct IndicesView: View {
    @EnvironmentObject var viewModel: MarketViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    regionSection(title: "🇺🇸 美股", items: viewModel.indices.us)
                    regionSection(title: "🇯🇵 日本", items: viewModel.indices.jp)
                    regionSection(title: "🇰🇷 韩国", items: viewModel.indices.kr)
                    regionSection(title: "🇭🇰 香港", items: viewModel.indices.hk)
                    regionSection(title: "🇨🇳 A股", items: viewModel.indices.cn)
                }
                .padding()
            }
            .background(AppTheme.Colors.background)
            .navigationTitle("全球指数")
            .refreshable {
                viewModel.loadData()
            }
        }
    }

    @ViewBuilder
    private func regionSection(title: String, items: [IndexItem]) -> some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                Text(title)
                    .font(.headline)
                    .foregroundColor(AppTheme.Colors.primaryText)

                ForEach(items) { item in
                    indexCard(item: item)
                }
            }
        }
    }

    private func indexCard(item: IndexItem) -> some View {
        HStack(spacing: 16) {
            VStack(alignment: .leading, spacing: 6) {
                Text(item.name)
                    .font(.headline)
                    .foregroundColor(AppTheme.Colors.primaryText)

                Text(String(format: "%.2f", item.value))
                    .font(.title)
                    .fontWeight(.bold)
                    .foregroundColor(AppTheme.Colors.primaryText)

                ChangeLabel(change: item.change, changePct: item.changePct)
            }

            Spacer()

            SparklineView(data: item.sparkline, isUp: item.isUp)
                .frame(width: 100, height: 50)
        }
        .cardStyle()
    }
}
```

**Step 2: Commit**

```bash
git add ios/MarketPulse/Views/Indices/
git commit -m "feat(ios): add Indices tab with region grouping"
```

---

### Task 22: Sectors tab

**Files:**
- Create: `ios/MarketPulse/Views/Sectors/SectorsListView.swift`

**Step 1: Create SectorsListView.swift**

```swift
import SwiftUI

struct SectorsListView: View {
    @EnvironmentObject var viewModel: MarketViewModel

    enum SortMode: String, CaseIterable {
        case gainers = "涨幅"
        case losers = "跌幅"
        case volume = "成交额"
    }

    @State private var sortMode: SortMode = .gainers

    private var sortedSectors: [SectorItem] {
        switch sortMode {
        case .gainers:
            return viewModel.sectors.sorted { $0.changePct > $1.changePct }
        case .losers:
            return viewModel.sectors.sorted { $0.changePct < $1.changePct }
        case .volume:
            return viewModel.sectors.sorted { ($0.turnover ?? 0) > ($1.turnover ?? 0) }
        }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Sort picker
                Picker("排序", selection: $sortMode) {
                    ForEach(SortMode.allCases, id: \.self) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                .padding()

                // Sector list
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(Array(sortedSectors.enumerated()), id: \.element.id) { index, sector in
                            HStack(spacing: 12) {
                                Text("\(index + 1)")
                                    .font(.caption)
                                    .fontWeight(.bold)
                                    .foregroundColor(AppTheme.Colors.secondaryText)
                                    .frame(width: 24)

                                Text(sector.name)
                                    .font(.subheadline)
                                    .foregroundColor(AppTheme.Colors.primaryText)

                                Spacer()

                                if let stock = sector.leadingStock, !stock.isEmpty {
                                    Text(stock)
                                        .font(.caption)
                                        .foregroundColor(AppTheme.Colors.secondaryText)
                                        .lineLimit(1)
                                }

                                Text(String(format: "%+.2f%%", sector.changePct))
                                    .font(.subheadline)
                                    .fontWeight(.bold)
                                    .foregroundColor(AppTheme.Colors.changeColor(isUp: sector.isUp))
                                    .frame(width: 75, alignment: .trailing)
                            }
                            .padding(.horizontal)
                            .padding(.vertical, 12)

                            Divider().padding(.leading, 48)
                        }
                    }
                }
            }
            .background(AppTheme.Colors.background)
            .navigationTitle("A股板块")
            .refreshable {
                viewModel.loadData()
            }
        }
    }
}
```

**Step 2: Commit**

```bash
git add ios/MarketPulse/Views/Sectors/
git commit -m "feat(ios): add Sectors tab with sort controls"
```

---

## Phase 9: Integration & Polish

### Task 23: End-to-end testing

**Step 1: Start Redis locally**

```bash
# If using Docker:
docker run -d --name redis -p 6379:6379 redis:alpine
# Or if using Homebrew:
brew services start redis
```

**Step 2: Create .env file for backend**

```bash
cd /Users/zyf/VibeCodes/MarketPulse/backend
cp .env.example .env
# Edit .env with your API keys:
# GOLDAPI_KEY=<get free key from goldapi.io>
# ALPHAVANTAGE_KEY=<get free key from alphavantage.co>
```

**Step 3: Start backend and verify**

```bash
cd /Users/zyf/VibeCodes/MarketPulse/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Test endpoints:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/overview
curl http://localhost:8000/api/v1/commodities
curl http://localhost:8000/api/v1/indices/cn
curl http://localhost:8000/api/v1/sectors/cn
```

**Step 4: Run iOS app in Xcode Simulator**

Open `ios/MarketPulse.xcodeproj` in Xcode, select iPhone 15 simulator, build and run. Verify data loads on all 4 tabs.

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration fixes from end-to-end testing"
```

---

### Task 24: iOS App Info.plist — allow local HTTP

**Files:**
- Modify: `ios/MarketPulse/Info.plist`

**Step 1: Add App Transport Security exception for localhost**

Add to Info.plist:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

**Step 2: Commit**

```bash
git add ios/MarketPulse/Info.plist
git commit -m "fix(ios): allow local HTTP networking for development"
```

---

## Phase 10: GitHub Upload

### Task 25: Push to GitHub

**Step 1: Create GitHub repo**

```bash
cd /Users/zyf/VibeCodes/MarketPulse
gh repo create MarketPulse --public --source=. --remote=origin --description="全球金融市场实时监控面板 - iOS App + Python Backend"
```

**Step 2: Push**

```bash
git push -u origin main
```

---

## Task Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1 | Git init + project structure |
| 2 | 2-4 | FastAPI skeleton, Redis cache, Pydantic models |
| 3 | 5-7 | Data fetchers (AKShare, Alpha Vantage, GoldAPI) |
| 4 | 8-11 | Scheduler, API routes, Docker |
| 5 | 12-14 | iOS project, models, API service |
| 6 | 15 | Theme system |
| 7 | 16 | ViewModel |
| 8 | 17-22 | iOS views (all 4 tabs + components) |
| 9 | 23-24 | Integration testing |
| 10 | 25 | GitHub upload |

**Total: 25 tasks, estimated ~3 hours of implementation time.**
