import Foundation

struct OverviewResponse: Codable, Equatable {
    let timestamp: String
    let commodities: [CommodityItem]
    let indices: IndexGroups
    let sectors: [SectorItem]

    static let sample = OverviewResponse(
        timestamp: "2026-03-16T10:30:00Z",
        commodities: [
            CommodityItem(
                symbol: "XAU",
                name: "黄金",
                nameEn: "Gold",
                price: 2650.30,
                change: 12.50,
                changePct: 0.47,
                high: 2655.0,
                low: 2635.0,
                unit: "USD/oz"
            ),
            CommodityItem(
                symbol: "WTI",
                name: "原油",
                nameEn: "Crude Oil",
                price: 78.30,
                change: -0.85,
                changePct: -1.07,
                high: 79.42,
                low: 77.88,
                unit: "USD/bbl"
            )
        ],
        indices: IndexGroups(
            us: [
                IndexItem(
                    symbol: "IXIC",
                    name: "纳斯达克",
                    value: 18250.0,
                    change: 125.3,
                    changePct: 0.69,
                    high: 18310.0,
                    low: 18140.0,
                    volume: 63_145_490,
                    sparkline: [18100, 18120, 18110, 18180, 18250]
                )
            ],
            jp: [],
            kr: [],
            hk: [],
            cn: [
                IndexItem(
                    symbol: "sh000001",
                    name: "上证指数",
                    value: 3050.12,
                    change: 10.5,
                    changePct: 0.35,
                    high: 3060,
                    low: 3038,
                    volume: 123_456_789,
                    sparkline: [3028, 3033, 3041, 3046, 3050]
                )
            ]
        ),
        sectors: [
            SectorItem(name: "半导体", changePct: 3.25, turnover: 12_500_000_000, leadingStock: "中芯国际"),
            SectorItem(name: "算力", changePct: 2.44, turnover: 9_300_000_000, leadingStock: "寒武纪")
        ]
    )
}

struct CommodityItem: Codable, Equatable, Identifiable {
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

struct IndexItem: Codable, Equatable, Identifiable {
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

struct IndexGroups: Codable, Equatable {
    let us: [IndexItem]
    let jp: [IndexItem]
    let kr: [IndexItem]
    let hk: [IndexItem]
    let cn: [IndexItem]

    static let empty = IndexGroups(us: [], jp: [], kr: [], hk: [], cn: [])
}

struct SectorItem: Codable, Equatable, Identifiable {
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

// MARK: - Chart Data

struct ChartPoint: Codable, Equatable {
    let time: String
    let price: Double
    let volume: Double?
}

struct ChartResponse: Codable {
    let timestamp: String
    let symbol: String
    let period: String
    let data: [ChartPoint]
}
