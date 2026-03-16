# MarketPulse - 全球金融市场监控面板设计文档

## 项目概述

MarketPulse 是一个全球金融市场实时监控 iOS 应用，聚合大宗商品、全球主要指数和中国 A 股板块数据，以精美的面板形式展示，支持深色/浅色双主题。

## 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| iOS 客户端 | Swift + SwiftUI + Swift Charts | 原生 iOS 开发 |
| 后端服务 | Python + FastAPI | 数据聚合中转层 |
| 缓存 | Redis (Upstash 免费版) | 缓存数据源响应，减少 API 调用 |
| 定时任务 | APScheduler | 定时从各数据源拉取数据 |
| 部署 | Railway / Render | 后端免费套餐 |

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────┐
│                  iOS App (Swift)                 │
│         SwiftUI + Charts + 深色/浅色主题          │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 大宗商品  │ │ 全球指数  │ │  A股指数 & 板块   │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│              ↕  REST API (每1-3分钟轮询)          │
└─────────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────────┐
│            FastAPI 后端 (Python)                  │
│                                                  │
│  ┌─────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ 调度器   │  │ API路由   │  │  Redis 缓存   │  │
│  │(APScheduler)│          │  │               │  │
│  └─────────┘  └──────────┘  └───────────────┘  │
│       ↓                                         │
│  ┌─────────────────────────────────────────┐    │
│  │           数据采集层 (Fetchers)           │    │
│  │  AKShare │ Alpha Vantage │ Finnhub │ ...│    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### 数据流

1. APScheduler 定时触发各 Fetcher 拉取数据
2. Fetcher 从各免费 API 抓取数据，标准化后写入 Redis
3. iOS App 定时轮询后端 REST API
4. 后端从 Redis 读取缓存数据返回给 App

## 数据源映射

| 数据类别 | 具体内容 | 数据源 | 刷新频率 |
|---------|---------|--------|---------|
| 大宗商品 | 黄金、白银、铜、原油 | Finnhub + GoldAPI.io | 1分钟 |
| 美股指数 | 纳斯达克、标普500、道琼斯 | Finnhub | 1分钟 |
| 日韩指数 | 日经225、KOSPI | Alpha Vantage | 5分钟 |
| 港股指数 | 恒生指数 | AKShare (新浪源) | 1分钟 |
| A股指数 | 上证、深证成指、创业板指、科创50 | AKShare (新浪源) | 1分钟 |
| A股板块 | 全行业板块（约30个） | AKShare | 3分钟 |

## API 端点设计

```
GET /api/v1/commodities        → 大宗商品（金银铜油）
GET /api/v1/indices/global      → 全球指数
GET /api/v1/indices/cn          → A股指数
GET /api/v1/sectors/cn          → A股行业板块
GET /api/v1/overview            → 聚合全部数据（App首页一次拉取）
```

### 响应格式示例

```json
{
  "timestamp": "2026-03-16T10:30:00Z",
  "commodities": [
    {
      "symbol": "XAU",
      "name": "黄金",
      "name_en": "Gold",
      "price": 2650.30,
      "change": 12.50,
      "change_pct": 0.47,
      "high": 2655.00,
      "low": 2635.00,
      "unit": "USD/oz"
    }
  ],
  "indices": {
    "us": [
      {
        "symbol": "IXIC",
        "name": "纳斯达克",
        "value": 18250.00,
        "change": 125.30,
        "change_pct": 0.69,
        "sparkline": [18100, 18120, ...]
      }
    ],
    "jp": [...],
    "kr": [...],
    "hk": [...],
    "cn": [...]
  },
  "sectors": [
    {
      "name": "半导体",
      "change_pct": 3.25,
      "volume": 12500000000,
      "leading_stock": "中芯国际"
    }
  ]
}
```

## iOS App 页面设计

### 页面结构（Tab 导航）

```
┌─────────────────────────────────────────┐
│              MarketPulse                │
├─────────┬─────────┬─────────┬──────────┤
│  总览    │  商品    │  指数   │  A股板块  │
│ Overview│Commodity│ Indices │ Sectors  │
└─────────┴─────────┴─────────┴──────────┘
```

### 各 Tab 内容

**1. 总览 Overview**
- 顶部：4个大宗商品卡片（金、银、铜、油），显示价格 + 涨跌幅 + 迷你折线图
- 中部：全球指数列表，按地区分组（美/日/韩/港/中），每行显示名称、点位、涨跌幅
- 底部：A股板块热力图（TreeMap），颜色深浅表示涨跌幅度，面积表示成交量

**2. 商品 Commodity**
- 金银铜油各一个详情卡片
- 点击进入日K线图（Swift Charts）
- 显示当日最高/最低/开盘/收盘

**3. 指数 Indices**
- 分区展示：🇺🇸 美股 / 🇯🇵 日本 / 🇰🇷 韩国 / 🇭🇰 香港 / 🇨🇳 A股
- 每个指数卡片：点位 + 涨跌幅 + 日内走势迷你图
- 点击进入详情：K线图 + 成交量

**4. A股板块 Sectors**
- 板块列表，默认按涨跌幅排序
- 每行：板块名、涨跌幅、领涨股
- 支持按涨幅/跌幅/成交额排序切换

### 主题配色

| 元素 | 深色模式 | 浅色模式 |
|------|---------|---------|
| 背景 | #0A0E17 | #F5F7FA |
| 卡片 | #151B28 | #FFFFFF |
| 涨 | #00E676 | #4CAF50 |
| 跌 | #FF1744 | #F44336 |
| 文字 | #E0E0E0 | #1A1A1A |
| 辅助文字 | #6B7280 | #9CA3AF |

## 项目结构

### 后端 (market-pulse-api/)

```
market-pulse-api/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 配置（API Keys、Redis URL）
│   ├── routers/
│   │   ├── commodities.py    # 大宗商品路由
│   │   ├── indices.py        # 全球指数路由
│   │   ├── sectors.py        # A股板块路由
│   │   └── overview.py       # 聚合接口路由
│   ├── fetchers/
│   │   ├── base.py           # Fetcher 基类
│   │   ├── akshare_fetcher.py
│   │   ├── finnhub_fetcher.py
│   │   ├── alphavantage_fetcher.py
│   │   └── goldapi_fetcher.py
│   ├── scheduler.py          # APScheduler 定时任务
│   ├── cache.py              # Redis 缓存封装
│   └── models.py             # Pydantic 数据模型
├── requirements.txt
├── Dockerfile
└── README.md
```

### iOS 客户端 (MarketPulse/)

```
MarketPulse/
├── MarketPulse.xcodeproj
├── MarketPulse/
│   ├── App/
│   │   ├── MarketPulseApp.swift
│   │   └── ContentView.swift
│   ├── Models/
│   │   ├── Commodity.swift
│   │   ├── Index.swift
│   │   └── Sector.swift
│   ├── Services/
│   │   ├── APIService.swift       # 网络请求
│   │   └── DataRefreshManager.swift # 定时刷新
│   ├── ViewModels/
│   │   ├── OverviewViewModel.swift
│   │   ├── CommodityViewModel.swift
│   │   ├── IndicesViewModel.swift
│   │   └── SectorsViewModel.swift
│   ├── Views/
│   │   ├── Overview/
│   │   │   ├── OverviewView.swift
│   │   │   ├── CommodityCardView.swift
│   │   │   ├── IndexRowView.swift
│   │   │   └── SectorHeatmapView.swift
│   │   ├── Commodity/
│   │   │   ├── CommodityListView.swift
│   │   │   └── CommodityDetailView.swift
│   │   ├── Indices/
│   │   │   ├── IndicesView.swift
│   │   │   └── IndexDetailView.swift
│   │   └── Sectors/
│   │       ├── SectorsListView.swift
│   │       └── SectorDetailView.swift
│   ├── Components/
│   │   ├── SparklineView.swift    # 迷你折线图
│   │   ├── KLineChartView.swift   # K线图
│   │   └── TreeMapView.swift      # 热力图
│   └── Theme/
│       ├── AppTheme.swift
│       └── Colors.swift
└── MarketPulseTests/
```

## GitHub 仓库结构

```
MarketPulse/
├── backend/          → market-pulse-api
├── ios/              → MarketPulse iOS App
├── docs/             → 设计文档
├── .gitignore
└── README.md
```

## 部署策略

- **后端**：Railway/Render 免费套餐，Docker 部署
- **Redis**：Upstash 免费版（10,000 命令/天）
- **iOS**：Xcode 本地构建，通过个人开发者账号部署到自己的 iPhone
