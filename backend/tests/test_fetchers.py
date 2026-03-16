from app.fetchers.akshare_fetcher import normalize_index_row, normalize_sector_row, normalize_ths_sector_row
from app.fetchers.base import build_sparkline
from app.fetchers.alphavantage_fetcher import (
    AVCommoditySpec,
    AVQuoteSpec,
    extract_commodity_item,
    extract_global_quote_item,
    is_rate_limited_response,
)
from app.fetchers.goldapi_fetcher import GoldSpec, extract_goldapi_item
from app.fetchers.stooq_fetcher import (
    STQ_COMMODITY_SPECS,
    STQ_HK_INDEX_SPECS,
    STQ_US_INDEX_SPECS,
    StooqCommoditySpec,
    StooqIndexSpec,
    extract_stooq_commodity_item,
    extract_stooq_hk_index_item,
    extract_stooq_index_item,
)
from app.scheduler import build_job_specs, refresh_cn_indices


def test_extract_global_quote_item_maps_etf_quote_to_index_shape():
    payload = {
        "01. symbol": "QQQ",
        "03. high": "603.5999",
        "04. low": "592.5700",
        "05. price": "593.7200",
        "06. volume": "63145490",
        "09. change": "-3.5400",
        "10. change percent": "-0.5927%",
    }

    result = extract_global_quote_item(
        payload,
        AVQuoteSpec(source_symbol="QQQ", market_symbol="IXIC", name="纳斯达克"),
    )

    assert result == {
        "symbol": "IXIC",
        "name": "纳斯达克",
        "value": 593.72,
        "change": -3.54,
        "change_pct": -0.5927,
        "high": 603.5999,
        "low": 592.57,
        "volume": 63145490.0,
        "sparkline": [],
    }


def test_extract_commodity_item_uses_latest_and_previous_values():
    payload = {
        "data": [
            {"date": "2026-01-01", "value": "12986.60681818182"},
            {"date": "2025-12-01", "value": "11790.96409090909"},
        ]
    }

    result = extract_commodity_item(
        payload,
        AVCommoditySpec(symbol="COPPER", function="COPPER", name="铜", name_en="Copper", unit="USD/ton"),
    )

    assert result == {
        "symbol": "COPPER",
        "name": "铜",
        "name_en": "Copper",
        "price": 12986.6068,
        "change": 1195.6427,
        "change_pct": 10.14,
        "high": 12986.6068,
        "low": 12986.6068,
        "unit": "USD/ton",
    }


def test_rate_limit_detection_matches_information_payload():
    assert is_rate_limited_response(
        {
            "Information": "Thank you for using Alpha Vantage! Please consider spreading out your free API requests more sparingly."
        }
    )


def test_extract_goldapi_item_maps_quote_fields():
    payload = {
        "price": 5013.745,
        "ch": -5.43,
        "chp": -0.11,
        "high_price": 5036.255,
        "low_price": 4967.61,
    }

    result = extract_goldapi_item(payload, GoldSpec(symbol="XAU", name="黄金", name_en="Gold", unit="USD/oz"))

    assert result == {
        "symbol": "XAU",
        "name": "黄金",
        "name_en": "Gold",
        "price": 5013.745,
        "change": -5.43,
        "change_pct": -0.11,
        "high": 5036.255,
        "low": 4967.61,
        "unit": "USD/oz",
    }


def test_normalize_akshare_rows():
    index = normalize_index_row(
        {
            "代码": "sh000001",
            "名称": "上证指数",
            "最新价": 3050.12,
            "涨跌额": 10.5,
            "涨跌幅": 0.35,
            "最高": 3060.0,
            "最低": 3038.0,
            "成交量": 123456789,
        }
    )
    sector = normalize_sector_row(
        {
            "板块名称": "半导体",
            "涨跌幅": 3.25,
            "总市值": 12500000000,
            "领涨股票": "中芯国际",
        }
    )

    assert index["symbol"] == "sh000001"
    assert index["volume"] == 123456789.0
    assert sector["leading_stock"] == "中芯国际"
    assert sector["change_pct"] == 3.25


def test_normalize_ths_sector_row():
    sector = normalize_ths_sector_row(
        {
            "板块": "半导体",
            "涨跌幅": 3.25,
            "总成交额": 12500000000,
            "领涨股": "中芯国际",
        }
    )

    assert sector == {
        "name": "半导体",
        "change_pct": 3.25,
        "turnover": 12500000000.0,
        "leading_stock": "中芯国际",
    }


def test_build_sparkline_uses_recent_numeric_values():
    assert build_sparkline([1, 2, "3.5", None, 4, 5, 6], limit=4) == [3.5, 4.0, 5.0, 6.0]


def test_extract_stooq_index_item_maps_quote_and_sparkline():
    result = extract_stooq_index_item(
        "2026-03-13,22425.71,22521.38,22069.24,22105.36,4681146300",
        StooqIndexSpec(symbol="^ndq", market_symbol="IXIC", name="纳斯达克"),
        sparkline=[21980.12, 22144.8, 22091.45, 22105.36],
    )

    assert result == {
        "symbol": "IXIC",
        "name": "纳斯达克",
        "value": 22105.36,
        "change": 13.91,
        "change_pct": 0.063,
        "high": 22521.38,
        "low": 22069.24,
        "volume": 4681146300.0,
        "sparkline": [21980.12, 22144.8, 22091.45, 22105.36],
    }


def test_extract_stooq_hk_index_item_maps_quote_and_sparkline():
    result = extract_stooq_hk_index_item(
        "2026-03-13,18588.63,18620.50,18388.10,18456.23,0",
        sparkline=[18720.0, 18690.0, 18580.0, 18456.23],
    )

    assert STQ_HK_INDEX_SPECS == (StooqIndexSpec(symbol="^hsi", market_symbol="HSI", name="恒生指数"),)
    assert result == {
        "symbol": "HSI",
        "name": "恒生指数",
        "value": 18456.23,
        "change": -132.4,
        "change_pct": -0.71,
        "high": 18620.5,
        "low": 18388.1,
        "volume": 0.0,
        "sparkline": [18720.0, 18690.0, 18580.0, 18456.23],
    }


def test_extract_stooq_commodity_item_maps_quote_fields():
    result = extract_stooq_commodity_item(
        "2026-03-16,97.84,99.26,93.4,94.28,",
        StooqCommoditySpec(symbol="cl.f", market_symbol="WTI", name="原油", name_en="Crude Oil", unit="USD/bbl"),
    )

    assert result == {
        "symbol": "WTI",
        "name": "原油",
        "name_en": "Crude Oil",
        "price": 94.28,
        "change": -3.56,
        "change_pct": -3.64,
        "high": 99.26,
        "low": 93.4,
        "unit": "USD/bbl",
    }


def test_stooq_specs_cover_expanded_dashboard_symbols():
    assert {spec.market_symbol for spec in STQ_US_INDEX_SPECS} == {"IXIC", "SPX", "DJI"}
    assert {spec.market_symbol for spec in STQ_COMMODITY_SPECS} >= {
        "WTI",
        "BRENT",
        "NATGAS",
        "COPPER",
        "CORN",
        "WHEAT",
        "COTTON",
        "SUGAR",
        "COFFEE",
    }


def test_scheduler_job_specs_reflect_free_tier_limits():
    specs = {spec["id"]: spec for spec in build_job_specs()}

    assert specs["cn_indices"]["minutes"] == 1
    assert specs["cn_sectors"]["minutes"] == 3
    assert specs["gold_metals"]["minutes"] == 15
    assert specs["global_indices"]["hours"] == 1
    assert specs["stooq_commodities"]["hours"] == 1


async def test_refresh_cn_indices_uses_stooq_hk_source(monkeypatch):
    async def fake_fetch_cn_indices(self):
        return [{"symbol": "sh000001", "name": "上证指数"}]

    async def fake_fetch_hk_indices(self):
        return [{"symbol": "HSI", "name": "恒生指数"}]

    async def fake_load_index_groups():
        return {"us": [], "jp": [], "kr": [], "hk": [], "cn": []}

    async def fake_cache_set(*args, **kwargs):
        return None

    monkeypatch.setattr("app.fetchers.akshare_fetcher.AKShareFetcher.fetch_cn_indices", fake_fetch_cn_indices)
    monkeypatch.setattr("app.fetchers.stooq_fetcher.StooqFetcher.fetch_hk_indices", fake_fetch_hk_indices)
    monkeypatch.setattr("app.scheduler.cache_set", fake_cache_set)
    monkeypatch.setattr("app.scheduler._load_index_groups", fake_load_index_groups)

    groups = await refresh_cn_indices()

    assert groups["cn"] == [{"symbol": "sh000001", "name": "上证指数"}]
    assert groups["hk"] == [{"symbol": "HSI", "name": "恒生指数"}]
