import Foundation

protocol MarketDataServicing: Sendable {
    func fetchOverview() async throws -> OverviewResponse
}

enum APIServiceError: LocalizedError {
    case invalidResponse
    case invalidStatusCode(Int)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Received an invalid server response."
        case .invalidStatusCode(let code):
            return "Server returned status code \(code)."
        }
    }
}

actor APIService: MarketDataServicing {
    static let shared = APIService()

    private let baseURL: URL
    private let session: URLSession
    private let decoder = JSONDecoder()

    init(baseURL: URL = APIService.defaultBaseURL, session: URLSession? = nil) {
        self.baseURL = baseURL
        if let session {
            self.session = session
        } else {
            let config = URLSessionConfiguration.default
            config.timeoutIntervalForRequest = 15
            config.timeoutIntervalForResource = 30
            self.session = URLSession(configuration: config)
        }
    }

    func fetchOverview() async throws -> OverviewResponse {
        let endpoint = baseURL.appending(path: "overview")
        let (data, response) = try await session.data(from: endpoint)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIServiceError.invalidResponse
        }

        guard (200 ... 299).contains(httpResponse.statusCode) else {
            throw APIServiceError.invalidStatusCode(httpResponse.statusCode)
        }

        return try decoder.decode(OverviewResponse.self, from: data)
    }

    func fetchChart(symbol: String, period: String = "1d") async throws -> ChartResponse {
        var components = URLComponents(url: baseURL.appending(path: "chart/intraday"), resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "symbol", value: symbol),
            URLQueryItem(name: "period", value: period),
        ]
        let (data, response) = try await session.data(from: components.url!)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIServiceError.invalidResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIServiceError.invalidStatusCode(httpResponse.statusCode)
        }
        return try decoder.decode(ChartResponse.self, from: data)
    }
}

private extension APIService {
    static var defaultBaseURL: URL {
        return URL(string: "http://47.102.109.227:8000/api/v1")!
    }
}
