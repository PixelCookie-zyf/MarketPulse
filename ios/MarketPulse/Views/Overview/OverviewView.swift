import SwiftUI

struct OverviewView: View {
    @EnvironmentObject private var viewModel: MarketViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    statusHeader

                    // Market status pills
                    marketStatusBar

                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                        ForEach(Array(viewModel.commodities.enumerated()), id: \.element.id) { index, item in
                            CommodityCardView(item: item)
                                .transition(.asymmetric(
                                    insertion: .opacity.combined(with: .move(edge: .bottom)),
                                    removal: .opacity
                                ))
                                .animation(
                                    .easeOut(duration: 0.3).delay(Double(index) * 0.05),
                                    value: viewModel.commodities
                                )
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

    // MARK: - Market Status Bar

    private var marketStatusBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                MarketStatusPill(name: "A股", isOpen: isMarketOpen(.cn))
                MarketStatusPill(name: "港股", isOpen: isMarketOpen(.hk))
                MarketStatusPill(name: "美股", isOpen: isMarketOpen(.us))
                MarketStatusPill(name: "日股", isOpen: isMarketOpen(.jp))
                MarketStatusPill(name: "韩股", isOpen: isMarketOpen(.kr))
            }
            .padding(.horizontal, 2)
        }
    }

    // MARK: - Market Open Logic

    private enum MarketRegion {
        case cn, hk, us, jp, kr
    }

    private func isMarketOpen(_ region: MarketRegion) -> Bool {
        let now = Date()

        let weekday: Int
        switch region {
        case .cn, .hk:
            let tz = TimeZone(identifier: "Asia/Shanghai")!
            var cal = Calendar.current
            cal.timeZone = tz
            weekday = cal.component(.weekday, from: now)
            guard weekday >= 2 && weekday <= 6 else { return false }
            return isWithinHours(now, timeZone: tz, openHour: 9, openMinute: 30,
                                 closeHour: region == .cn ? 15 : 16, closeMinute: 0)
        case .us:
            let tz = TimeZone(identifier: "America/New_York")!
            var cal = Calendar.current
            cal.timeZone = tz
            weekday = cal.component(.weekday, from: now)
            guard weekday >= 2 && weekday <= 6 else { return false }
            return isWithinHours(now, timeZone: tz, openHour: 9, openMinute: 30,
                                 closeHour: 16, closeMinute: 0)
        case .jp:
            let tz = TimeZone(identifier: "Asia/Tokyo")!
            var cal = Calendar.current
            cal.timeZone = tz
            weekday = cal.component(.weekday, from: now)
            guard weekday >= 2 && weekday <= 6 else { return false }
            return isWithinHours(now, timeZone: tz, openHour: 9, openMinute: 0,
                                 closeHour: 15, closeMinute: 0)
        case .kr:
            let tz = TimeZone(identifier: "Asia/Seoul")!
            var cal = Calendar.current
            cal.timeZone = tz
            weekday = cal.component(.weekday, from: now)
            guard weekday >= 2 && weekday <= 6 else { return false }
            return isWithinHours(now, timeZone: tz, openHour: 9, openMinute: 0,
                                 closeHour: 15, closeMinute: 30)
        }
    }

    private func isWithinHours(_ date: Date, timeZone: TimeZone,
                                openHour: Int, openMinute: Int,
                                closeHour: Int, closeMinute: Int) -> Bool {
        var calendar = Calendar.current
        calendar.timeZone = timeZone
        let hour = calendar.component(.hour, from: date)
        let minute = calendar.component(.minute, from: date)
        let totalMinutes = hour * 60 + minute
        let openTotal = openHour * 60 + openMinute
        let closeTotal = closeHour * 60 + closeMinute
        return totalMinutes >= openTotal && totalMinutes < closeTotal
    }

    // MARK: - Status Header

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

    // MARK: - Sectors Preview (horizontal scrolling tags)

    private var sectorsPreview: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("A股板块热度")
                .font(.title3.weight(.bold))
                .foregroundStyle(AppTheme.Colors.primaryText)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(viewModel.sectors.prefix(10)) { sector in
                        sectorTag(sector)
                    }
                }
                .padding(.horizontal, 2)
            }
        }
    }

    private func sectorTag(_ sector: SectorItem) -> some View {
        let color = AppTheme.Colors.changeColor(isUp: sector.isUp)
        return HStack(spacing: 4) {
            Text(sector.name)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(AppTheme.Colors.primaryText)
            Text(String(format: "%+.2f%%", sector.changePct))
                .font(.caption.weight(.bold))
                .foregroundStyle(color)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(color.opacity(0.08))
        .clipShape(Capsule())
        .overlay(
            Capsule()
                .stroke(color.opacity(0.15), lineWidth: 1)
        )
    }
}

// MARK: - MarketStatusPill

private struct MarketStatusPill: View {
    let name: String
    let isOpen: Bool

    var body: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(isOpen ? Color.green : Color.gray)
                .frame(width: 6, height: 6)
            Text(name)
                .font(.caption.weight(.medium))
                .foregroundStyle(isOpen ? AppTheme.Colors.primaryText : AppTheme.Colors.secondaryText)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            isOpen
                ? Color.green.opacity(0.08)
                : AppTheme.Colors.cardBackground
        )
        .clipShape(Capsule())
        .overlay(
            Capsule()
                .stroke(
                    isOpen ? Color.green.opacity(0.2) : Color.gray.opacity(0.15),
                    lineWidth: 1
                )
        )
    }
}
