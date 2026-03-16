import SwiftUI

struct OverviewView: View {
    @EnvironmentObject private var viewModel: MarketViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    statusHeader

                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                        ForEach(viewModel.commodities) { item in
                            CommodityCardView(item: item)
                        }
                    }

                    indexSection(title: "全球指数", groups: groupedSections)
                    sectorsPreview
                }
                .padding(16)
            }
            .background(AppTheme.Colors.background.ignoresSafeArea())
            .navigationTitle("MarketPulse")
            .toolbarTitleDisplayMode(.large)
            .refreshable {
                await viewModel.loadData()
            }
        }
    }

    private var statusHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Error message
            if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(AppTheme.Colors.changeColor(isUp: false))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(AppTheme.Colors.cardBackground)
                    .clipShape(Capsule())
            }

            // Syncing banner — shown when loading with cached data visible
            if viewModel.isSyncing && !viewModel.commodities.isEmpty {
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                        .tint(AppTheme.Colors.accent)
                    Text("正在同步最新数据…")
                        .font(.footnote)
                        .foregroundStyle(AppTheme.Colors.secondaryText)
                }
            }

            // Data timestamp
            if let timestamp = viewModel.dataTimestamp {
                HStack(spacing: 4) {
                    Image(systemName: viewModel.isShowingCachedData ? "clock.arrow.circlepath" : "checkmark.circle.fill")
                        .font(.caption2)
                        .foregroundStyle(viewModel.isShowingCachedData ? AppTheme.Colors.secondaryText : .green)
                    Text(dataTimestampText(timestamp))
                        .font(.footnote)
                        .foregroundStyle(AppTheme.Colors.secondaryText)
                }
            }

            // Full-screen spinner only when no data at all
            if viewModel.isLoading && viewModel.commodities.isEmpty {
                ProgressView("同步市场数据中…")
                    .tint(AppTheme.Colors.accent)
            }
        }
    }

    private func dataTimestampText(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")

        if Calendar.current.isDateInToday(date) {
            formatter.dateFormat = "HH:mm"
            let timeStr = formatter.string(from: date)
            if viewModel.isShowingCachedData {
                return "数据更新时间 \(timeStr)（缓存）"
            } else {
                return "数据已同步 · \(timeStr)"
            }
        } else {
            formatter.dateFormat = "MM-dd HH:mm"
            let timeStr = formatter.string(from: date)
            if viewModel.isShowingCachedData {
                return "数据更新时间 \(timeStr)（缓存）"
            } else {
                return "数据已同步 · \(timeStr)"
            }
        }
    }

    private var groupedSections: [(String, [IndexItem])] {
        [
            ("美股", viewModel.indices.us),
            ("日本", viewModel.indices.jp),
            ("韩国", viewModel.indices.kr),
            ("香港", viewModel.indices.hk),
            ("A股", viewModel.indices.cn)
        ].filter { !$0.1.isEmpty }
    }

    private func indexSection(title: String, groups: [(String, [IndexItem])]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.title3.weight(.bold))
                .foregroundStyle(AppTheme.Colors.primaryText)

            ForEach(groups, id: \.0) { group in
                VStack(alignment: .leading, spacing: 8) {
                    Text(group.0)
                        .font(.headline)
                        .foregroundStyle(AppTheme.Colors.secondaryText)

                    VStack(spacing: 0) {
                        ForEach(group.1) { item in
                            IndexRowView(item: item)
                            if item.id != group.1.last?.id {
                                Divider()
                            }
                        }
                    }
                    .marketCardStyle()
                }
            }
        }
    }

    private var sectorsPreview: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("A股板块热度")
                .font(.title3.weight(.bold))
                .foregroundStyle(AppTheme.Colors.primaryText)

            VStack(spacing: 12) {
                ForEach(Array(viewModel.sectors.prefix(6))) { sector in
                    HStack {
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

                        Text(sector.changePct, format: .number.precision(.fractionLength(2)))
                            .font(.headline.weight(.bold))
                            .foregroundStyle(AppTheme.Colors.changeColor(isUp: sector.isUp))
                            + Text("%")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.Colors.changeColor(isUp: sector.isUp))
                    }
                }
            }
            .marketCardStyle()
        }
    }
}
