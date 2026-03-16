import XCTest
@testable import MarketPulse

final class MarketPulseTests: XCTestCase {
    func testNormalizeSparklineDataExpandsTightRangeWithPadding() {
        let result = normalizeSparklineData([4124.194, 4096.602, 4123.138, 4133.433, 4129.103, 4095.449, 4084.786])

        XCTAssertEqual(result.count, 7)
        XCTAssertEqual(result.first, 0.7605, accuracy: 0.001)
        XCTAssertEqual(result.last, 0.08, accuracy: 0.001)
        XCTAssertGreaterThan(result.max() ?? 0, 0.9)
        XCTAssertLessThan(result.min() ?? 1, 0.1)
    }

    func testOverviewResponseDecodesSnakeCasePayload() throws {
        let data = Data(
            """
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
                  "high": 2655.0,
                  "low": 2635.0,
                  "unit": "USD/oz"
                }
              ],
              "indices": {
                "us": [
                  {
                    "symbol": "IXIC",
                    "name": "纳斯达克",
                    "value": 18250.0,
                    "change": 125.3,
                    "change_pct": 0.69,
                    "sparkline": [18100, 18120]
                  }
                ],
                "jp": [],
                "kr": [],
                "hk": [],
                "cn": []
              },
              "sectors": [
                {
                  "name": "半导体",
                  "change_pct": 3.25,
                  "turnover": 12500000000,
                  "leading_stock": "中芯国际"
                }
              ]
            }
            """.utf8
        )

        let response = try JSONDecoder().decode(OverviewResponse.self, from: data)

        XCTAssertEqual(response.commodities.first?.nameEn, "Gold")
        XCTAssertEqual(response.indices.us.first?.symbol, "IXIC")
        XCTAssertEqual(response.sectors.first?.leadingStock, "中芯国际")
    }

    @MainActor
    func testMarketViewModelLoadsOverviewFromService() async {
        let service = MockMarketDataService(response: .sample)
        let viewModel = MarketViewModel(service: service)

        await viewModel.loadData()

        XCTAssertEqual(viewModel.commodities.count, 2)
        XCTAssertEqual(viewModel.indices.us.first?.symbol, "IXIC")
        XCTAssertEqual(viewModel.sectors.first?.name, "半导体")
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.errorMessage)
    }
}

private struct MockMarketDataService: MarketDataServicing {
    let response: OverviewResponse

    func fetchOverview() async throws -> OverviewResponse {
        response
    }
}
