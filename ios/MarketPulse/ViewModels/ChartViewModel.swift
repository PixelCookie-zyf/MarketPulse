import Foundation

@MainActor
final class ChartViewModel: ObservableObject {
    @Published var chartPoints: [ChartPoint] = []
    @Published var isLoading = false
    @Published var selectedPeriod: ChartPeriod

    enum ChartPeriod: String, CaseIterable {
        case oneDay = "1d"
        case fiveDay = "5d"

        var displayName: String {
            switch self {
            case .oneDay: "分时"
            case .fiveDay: "5日"
            }
        }
    }

    let symbol: String
    let name: String
    let isGlobalIndex: Bool

    private static let globalIndexSymbols: Set<String> = ["IXIC", "SPX", "DJI", "HSI", "N225", "KOSPI"]

    init(symbol: String, name: String) {
        self.symbol = symbol
        self.name = name
        self.isGlobalIndex = Self.globalIndexSymbols.contains(symbol)
        self.selectedPeriod = self.isGlobalIndex ? .fiveDay : .oneDay
    }

    func loadChart() async {
        isLoading = true
        defer { isLoading = false }

        if selectedPeriod == .fiveDay {
            await loadFiveDayChart()
        } else {
            await loadOneDayChart()
        }
    }

    private func loadOneDayChart() async {
        do {
            let response = try await APIService.shared.fetchChart(symbol: symbol, period: "1d")
            chartPoints = response.data
        } catch {
            print("[ChartVM] 1d load error: \(error)")
        }
    }

    private func loadFiveDayChart() async {
        // For 5-day: load from server (backend handles the period)
        do {
            let response = try await APIService.shared.fetchChart(symbol: symbol, period: "5d")
            chartPoints = response.data
        } catch {
            print("[ChartVM] 5d load error: \(error)")
        }
    }
}
