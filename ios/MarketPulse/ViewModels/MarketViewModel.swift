import Foundation

@MainActor
final class MarketViewModel: ObservableObject {
    @Published var commodities: [CommodityItem] = []
    @Published var indices: IndexGroups = .empty
    @Published var sectors: [SectorItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var lastUpdated: Date?

    private let service: MarketDataServicing
    private var refreshTask: Task<Void, Never>?

    init(service: MarketDataServicing = APIService.shared) {
        self.service = service
    }

    deinit {
        refreshTask?.cancel()
    }

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

    func loadData() async {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil

        defer { isLoading = false }

        do {
            let response = try await service.fetchOverview()
            commodities = response.commodities
            indices = response.indices
            sectors = response.sectors
            lastUpdated = Date()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
