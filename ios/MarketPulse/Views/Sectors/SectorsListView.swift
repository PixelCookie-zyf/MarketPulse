import SwiftUI

struct SectorsListView: View {
    @EnvironmentObject private var viewModel: MarketViewModel
    @State private var sortMode: SortMode = .gainers

    enum SortMode: String, CaseIterable {
        case gainers = "涨幅"
        case losers = "跌幅"
        case turnover = "成交额"
    }

    private var sortedSectors: [SectorItem] {
        switch sortMode {
        case .gainers:
            return viewModel.sectors.sorted { $0.changePct > $1.changePct }
        case .losers:
            return viewModel.sectors.sorted { $0.changePct < $1.changePct }
        case .turnover:
            return viewModel.sectors.sorted { ($0.turnover ?? 0) > ($1.turnover ?? 0) }
        }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Picker("排序", selection: $sortMode) {
                    ForEach(SortMode.allCases, id: \.self) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                .padding(16)

                ScrollView {
                    LazyVStack(spacing: 10) {
                        ForEach(Array(sortedSectors.enumerated()), id: \.element.id) { index, sector in
                            HStack(spacing: 12) {
                                Text("\(index + 1)")
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(AppTheme.Colors.secondaryText)
                                    .frame(width: 24)

                                VStack(alignment: .leading, spacing: 4) {
                                    Text(sector.name)
                                        .font(.subheadline.weight(.semibold))
                                        .foregroundStyle(AppTheme.Colors.primaryText)
                                    if let leadingStock = sector.leadingStock, !leadingStock.isEmpty {
                                        Text(leadingStock)
                                            .font(.caption)
                                            .foregroundStyle(AppTheme.Colors.secondaryText)
                                    }
                                }

                                Spacer()

                                if let turnover = sector.turnover {
                                    Text(turnover, format: .number.notation(.compactName))
                                        .font(.caption)
                                        .foregroundStyle(AppTheme.Colors.secondaryText)
                                }

                                Text("\(sector.changePct, specifier: "%+.2f")%")
                                    .font(.subheadline.weight(.bold))
                                    .foregroundStyle(AppTheme.Colors.changeColor(isUp: sector.isUp))
                                    .frame(width: 72, alignment: .trailing)
                            }
                            .marketCardStyle()
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 16)
                }
            }
            .background(AppTheme.Colors.background.ignoresSafeArea())
            .navigationTitle("A股板块")
            .refreshable {
                await viewModel.loadData()
            }
        }
    }
}
