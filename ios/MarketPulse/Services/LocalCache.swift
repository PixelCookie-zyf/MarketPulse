import Foundation

/// Persists the latest OverviewResponse to disk so the app can show
/// cached data immediately on next launch while fresh data syncs.
enum LocalCache {
    private static let fileName = "cached_overview.json"

    private static var fileURL: URL {
        let dir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        return dir.appending(path: fileName)
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
}

struct CachedOverview: Codable {
    let savedAt: Date
    let response: OverviewResponse
}
