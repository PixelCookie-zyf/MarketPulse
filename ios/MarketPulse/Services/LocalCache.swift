import Foundation

/// Persists the latest OverviewResponse to disk so the app can show
/// cached data immediately on next launch while fresh data syncs.
enum LocalCache {
    private static let fileName = "cached_overview.json"

    private static var cacheDirectory: URL {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
    }

    private static var fileURL: URL {
        cacheDirectory.appending(path: fileName)
    }

    /// Save response + the time it was cached.
    static func save(_ response: OverviewResponse) {
        let wrapper = CachedOverview(
            savedAt: Date(),
            response: response
        )
        do {
            let data = try JSONEncoder().encode(wrapper)
            try data.write(to: fileURL, options: .atomic)
        } catch {
            print("[LocalCache] save failed: \(error)")
        }
    }

    /// Load the most recent cached response, if any.
    static func load() -> CachedOverview? {
        guard FileManager.default.fileExists(atPath: fileURL.path()) else { return nil }
        do {
            let data = try Data(contentsOf: fileURL)
            return try JSONDecoder().decode(CachedOverview.self, from: data)
        } catch {
            print("[LocalCache] load failed: \(error)")
            return nil
        }
    }

    // MARK: - Chart History Cache

    static func saveChartHistory(_ data: [ChartPoint], symbol: String, date: String) {
        let fileName = "chart_\(symbol)_\(date).json"
        let url = cacheDirectory.appending(path: fileName)
        do {
            let encoded = try JSONEncoder().encode(data)
            try encoded.write(to: url, options: .atomic)
        } catch {
            print("[LocalCache] saveChartHistory failed: \(error)")
        }
    }

    static func loadChartHistory(symbol: String, date: String) -> [ChartPoint]? {
        let fileName = "chart_\(symbol)_\(date).json"
        let url = cacheDirectory.appending(path: fileName)
        guard FileManager.default.fileExists(atPath: url.path()) else { return nil }
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode([ChartPoint].self, from: data)
        } catch {
            print("[LocalCache] loadChartHistory failed: \(error)")
            return nil
        }
    }
}

struct CachedOverview: Codable {
    let savedAt: Date
    let response: OverviewResponse
}
