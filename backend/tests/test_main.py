from httpx import ASGITransport, AsyncClient

from app.cache import cache_set, close_cache, init_cache
from app.main import app


async def test_health_endpoint():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_root_endpoint_returns_service_metadata():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "MarketPulse API",
        "status": "ok",
        "routes": ["/health", "/api/v1/overview"],
    }


async def test_overview_endpoint_aggregates_cached_payloads():
    await init_cache()
    await cache_set(
        "commodities:all",
        [
            {
                "symbol": "XAU",
                "name": "黄金",
                "name_en": "Gold",
                "price": 2650.3,
                "change": 12.5,
                "change_pct": 0.47,
                "high": 2655.0,
                "low": 2635.0,
                "unit": "USD/oz",
            }
        ],
    )
    await cache_set(
        "indices:groups",
        {
            "us": [{"symbol": "IXIC", "name": "纳斯达克", "value": 18250.0, "change": 125.3, "change_pct": 0.69, "sparkline": []}],
            "jp": [],
            "kr": [],
            "hk": [],
            "cn": [],
        },
    )
    await cache_set(
        "sectors:cn",
        [{"name": "半导体", "change_pct": 3.25, "turnover": 12500000000, "leading_stock": "中芯国际"}],
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/overview")

    body = response.json()
    assert response.status_code == 200
    assert body["commodities"][0]["symbol"] == "XAU"
    assert body["indices"]["us"][0]["symbol"] == "IXIC"
    assert body["sectors"][0]["name"] == "半导体"
    assert "timestamp" in body

    await close_cache()


async def test_overview_endpoint_populates_data_on_cache_miss(monkeypatch):
    import app.scheduler as scheduler

    await init_cache()
    called = 0

    async def fake_ensure_market_data(*, include: set[str] | None = None):
        nonlocal called
        called += 1
        await cache_set(
            "commodities:all",
            [
                {
                    "symbol": "XAU",
                    "name": "黄金",
                    "name_en": "Gold",
                    "price": 2650.3,
                    "change": 12.5,
                    "change_pct": 0.47,
                    "high": 2655.0,
                    "low": 2635.0,
                    "unit": "USD/oz",
                }
            ],
        )
        await cache_set(
            "indices:groups",
            {
                "us": [{"symbol": "IXIC", "name": "纳斯达克", "value": 18250.0, "change": 125.3, "change_pct": 0.69, "sparkline": []}],
                "jp": [],
                "kr": [],
                "hk": [],
                "cn": [],
            },
        )
        await cache_set(
            "sectors:cn",
            [{"name": "半导体", "change_pct": 3.25, "turnover": 12500000000, "leading_stock": "中芯国际"}],
        )

    monkeypatch.setattr(scheduler, "ensure_market_data", fake_ensure_market_data, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/overview")

    body = response.json()
    assert response.status_code == 200
    assert body["commodities"][0]["symbol"] == "XAU"
    assert body["indices"]["us"][0]["symbol"] == "IXIC"
    assert body["sectors"][0]["name"] == "半导体"
    assert called == 1

    await close_cache()


async def test_overview_endpoint_blocks_for_missing_sectors(monkeypatch):
    import app.scheduler as scheduler

    await close_cache()
    await init_cache()
    await cache_set(
        "commodities:all",
        [
            {
                "symbol": "BRENT",
                "name": "布伦特原油",
                "name_en": "Brent Oil",
                "price": 74.5,
                "change": 0.30,
                "change_pct": 0.40,
                "high": 75.0,
                "low": 74.0,
                "unit": "USD/bbl",
            }
        ],
    )
    await cache_set(
        "indices:groups",
        {
            "us": [{"symbol": "DJI", "name": "道琼斯", "value": 42345.0, "change": 125.0, "change_pct": 0.29, "sparkline": [42010.0, 42100.0, 42345.0]}],
            "jp": [],
            "kr": [],
            "hk": [],
            "cn": [],
        },
    )

    calls: list[set[str] | None] = []

    async def fake_ensure_market_data(*, include: set[str] | None = None):
        calls.append(include)
        if include == {"sectors"}:
            await cache_set(
                "sectors:cn",
                [{"name": "半导体", "change_pct": 3.25, "turnover": 12500000000, "leading_stock": "中芯国际"}],
            )

    monkeypatch.setattr(scheduler, "ensure_market_data", fake_ensure_market_data, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/overview")

    body = response.json()
    assert response.status_code == 200
    assert body["sectors"][0]["name"] == "半导体"
    assert calls == [{"sectors"}]

    await close_cache()


async def test_commodities_endpoint_rebuilds_combined_cache_in_dashboard_order():
    await close_cache()
    await init_cache()
    await cache_set(
        "commodities:metals",
        [
            {"symbol": "XAG", "name": "白银"},
            {"symbol": "XAU", "name": "黄金"},
        ],
    )
    await cache_set(
        "commodities:em",
        [
            {"symbol": "COFFEE", "name": "咖啡"},
            {"symbol": "BRENT", "name": "布伦特原油"},
        ],
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/commodities")

    body = response.json()
    assert response.status_code == 200
    assert [item["symbol"] for item in body["data"]] == ["XAU", "XAG", "BRENT", "COFFEE"]

    await close_cache()


async def test_chart_endpoint_routes_global_indices_to_dedicated_fetcher(monkeypatch):
    await close_cache()
    await init_cache()

    called = {"global": 0, "commodity": 0}

    async def fake_fetch_global_index_chart(self, symbol: str, period: str):
        called["global"] += 1
        return [{"time": "2026-03-17 09:30", "price": 24706.4, "volume": 0.0}]

    async def fake_fetch_commodity_intraday(self, symbol: str):
        called["commodity"] += 1
        return [{"time": "00:00", "price": 0.0, "volume": 0.0}]

    monkeypatch.setattr(
        "app.fetchers.akshare_fetcher.AKShareFetcher.fetch_global_index_chart",
        fake_fetch_global_index_chart,
        raising=False,
    )
    monkeypatch.setattr(
        "app.fetchers.akshare_fetcher.AKShareFetcher.fetch_commodity_intraday",
        fake_fetch_commodity_intraday,
        raising=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/chart/intraday",
            params={"symbol": "IXIC", "period": "1d"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["data"] == [{"time": "2026-03-17 09:30", "price": 24706.4, "volume": 0.0}]
    assert called == {"global": 1, "commodity": 0}

    await close_cache()
