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
from app.scheduler import build_job_specs


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


def test_scheduler_job_specs_reflect_free_tier_limits():
    specs = {spec["id"]: spec for spec in build_job_specs()}

    assert specs["cn_indices"]["minutes"] == 1
    assert specs["cn_sectors"]["minutes"] == 3
    assert specs["gold_metals"]["minutes"] == 15
    assert specs["alpha_indices"]["hours"] == 12
    assert specs["alpha_commodities"]["hours"] == 12
