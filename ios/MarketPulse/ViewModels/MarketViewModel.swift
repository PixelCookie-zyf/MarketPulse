import Foundation

@MainActor
final class MarketViewModel: ObservableObject {
    @Published var commodities: [CommodityItem] = []
    @Published var indices: IndexGroups = .empty
    @Published var sectors: [SectorItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    /// Time the currently displayed data was produced by the server.
    @Published var dataTimestamp: Date?
    /// Whether the data on screen came from local cache (not yet refreshed).
    @Published var isShowingCachedData = false
    /// True while a network request is in flight (even if cached data is shown).
    @Published var isSyncing = false

    private let service: MarketDataServicing
    private var refreshTask: Task<Void, Never>?

    init(service: MarketDataServicing = APIService.shared) {
        self.service = service
        loadFromLocalCache()
    }

    deinit {
        refreshTask?.cancel()
    }

    // MARK: - Local cache bootstrap

    /// Called once at init — instantly populates the UI with whatever was
    /// saved last time so the user never stares at a blank screen.
    private func loadFromLocalCache() {
        guard let cached = LocalCache.load() else { return }
        applyResponse(cached.response)
        dataTimestamp = cached.savedAt
        isShowingCachedData = true
    }

    // MARK: - Auto-refresh

    func startAutoRefresh(interval: Duration = .seconds(60)) {
        guard refreshTask == nil else { return }

        refreshTask = Task { [weak self] in
            guard let self else { return }

            await self.loadData()
            while !Task.isCancelled {
                try? await Task.sleep(for: interval)
                if Task.isCancelled { break }
                await self.loadData()
            }
        }
    }

    func stopAutoRefresh() {
        refreshTask?.cancel()
        refreshTask = nil
    }

    // MARK: - Network fetch

    func loadData() async {
        guard !isLoading else { return }
        isLoading = true
        isSyncing = true
        errorMessage = nil

        defer {
            isLoading = false
            isSyncing = false
        }

        do {
            let response = try await service.fetchOverview()
            applyResponse(response)
            dataTimestamp = Date()
            isShowingCachedData = false

            // Persist for next launch
            LocalCache.save(response)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    // MARK: - Helpers

    private func applyResponse(_ response: OverviewResponse) {
        commodities = response.commodities
        indices = response.indices
        sectors = response.sectors
    }
}
