import Foundation

protocol MarketDataServicing {
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

    init(baseURL: URL = APIService.defaultBaseURL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
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
}

private extension APIService {
    static var defaultBaseURL: URL {
        #if DEBUG
        return URL(string: "http://127.0.0.1:8000/api/v1")!
        #else
        return URL(string: "https://your-backend.railway.app/api/v1")!
        #endif
    }
}
