import SwiftUI
import Charts

struct ChartDetailView: View {
    @StateObject private var viewModel: ChartViewModel
    @Environment(\.dismiss) private var dismiss

    let currentPrice: Double
    let change: Double
    let changePct: Double

    // Crosshair state
    @State private var selectedIndex: Int?

    init(symbol: String, name: String, currentPrice: Double, change: Double, changePct: Double) {
        _viewModel = StateObject(wrappedValue: ChartViewModel(symbol: symbol, name: name))
        self.currentPrice = currentPrice
        self.change = change
        self.changePct = changePct
    }

    private var isUp: Bool { change >= 0 }
    private var changeColor: Color { AppTheme.Colors.changeColor(isUp: isUp) }
    private var chartLineColor: Color { Color(hex: 0x3B82F6) } // Blue

    /// The point currently under the crosshair, or nil.
    private var selectedPoint: ChartPoint? {
        guard let idx = selectedIndex,
              idx >= 0,
              idx < viewModel.chartPoints.count else { return nil }
        return viewModel.chartPoints[idx]
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    priceHeader
                    periodPicker
                    chartView
                    statsGrid
                }
                .padding(16)
            }
            .background(AppTheme.Colors.background.ignoresSafeArea())
            .navigationTitle(viewModel.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(AppTheme.Colors.secondaryText)
                    }
                }
            }
            .task {
                await viewModel.loadChart()
            }
        }
    }

    // MARK: - Price Header

    private var priceHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Show selected point price when crosshair is active
            let displayPrice = selectedPoint?.price ?? currentPrice

            Text(String(format: "%.2f", displayPrice))
                .font(.system(size: 40, weight: .heavy, design: .rounded))
                .foregroundStyle(AppTheme.Colors.primaryText)
                .contentTransition(.numericText())
                .animation(.easeOut(duration: 0.1), value: selectedIndex)

            if let point = selectedPoint {
                // Show time of selected point
                Text(point.time)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(AppTheme.Colors.secondaryText)
            } else {
                HStack(spacing: 8) {
                    Text(String(format: "%+.2f", change))
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(changeColor)
                    Text(String(format: "(%+.2f%%)", changePct))
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(changeColor)
                }
            }
        }
    }

    // MARK: - Period Picker

    private var periodPicker: some View {
        HStack(spacing: 0) {
            ForEach(ChartViewModel.ChartPeriod.allCases, id: \.self) { period in
                Button {
                    selectedIndex = nil
                    withAnimation(.easeInOut(duration: 0.2)) {
                        viewModel.selectedPeriod = period
                    }
                    Task { await viewModel.loadChart() }
                } label: {
                    Text(period.displayName)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(viewModel.selectedPeriod == period ? AppTheme.Colors.primaryText : AppTheme.Colors.secondaryText)
                        .padding(.vertical, 8)
                        .padding(.horizontal, 20)
                        .background(
                            viewModel.selectedPeriod == period
                                ? chartLineColor.opacity(0.15)
                                : Color.clear
                        )
                        .clipShape(Capsule())
                }
            }
        }
        .padding(4)
        .background(AppTheme.Colors.cardBackground.opacity(0.5))
        .clipShape(Capsule())
    }

    // MARK: - Chart

    @ViewBuilder
    private var chartView: some View {
        if viewModel.isLoading {
            ProgressView()
                .frame(height: 280)
                .frame(maxWidth: .infinity)
        } else if viewModel.chartPoints.isEmpty {
            Text("暂无分时数据")
                .foregroundStyle(AppTheme.Colors.secondaryText)
                .frame(height: 280)
                .frame(maxWidth: .infinity)
        } else {
            let prices = viewModel.chartPoints.map(\.price)
            let minPrice = prices.min() ?? 0
            let maxPrice = prices.max() ?? 0
            let padding = max((maxPrice - minPrice) * 0.1, maxPrice * 0.002)
            let yMin = minPrice - padding
            let yMax = maxPrice + padding
            let pointCount = viewModel.chartPoints.count

            Chart {
                ForEach(Array(viewModel.chartPoints.enumerated()), id: \.offset) { index, point in
                    LineMark(
                        x: .value("Time", index),
                        y: .value("Price", point.price)
                    )
                    .foregroundStyle(chartLineColor)
                    .lineStyle(StrokeStyle(lineWidth: 2))
                    .interpolationMethod(.catmullRom)

                    AreaMark(
                        x: .value("Time", index),
                        yStart: .value("Min", yMin),
                        yEnd: .value("Price", point.price)
                    )
                    .foregroundStyle(
                        LinearGradient(
                            colors: [chartLineColor.opacity(0.2), chartLineColor.opacity(0.02)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .interpolationMethod(.catmullRom)
                }

                // Crosshair
                if let idx = selectedIndex, let point = selectedPoint {
                    // Vertical line
                    RuleMark(x: .value("Selected", idx))
                        .foregroundStyle(AppTheme.Colors.secondaryText.opacity(0.6))
                        .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))

                    // Horizontal line
                    RuleMark(y: .value("Price", point.price))
                        .foregroundStyle(AppTheme.Colors.secondaryText.opacity(0.6))
                        .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))

                    // Dot at intersection
                    PointMark(
                        x: .value("Selected", idx),
                        y: .value("Price", point.price)
                    )
                    .symbol(Circle())
                    .symbolSize(60)
                    .foregroundStyle(chartLineColor)

                    // Price label on Y axis
                    PointMark(
                        x: .value("Selected", idx),
                        y: .value("Price", point.price)
                    )
                    .symbol(Circle())
                    .symbolSize(0)
                    .annotation(position: .topTrailing, spacing: 6) {
                        Text(String(format: "%.2f", point.price))
                            .font(.caption2.weight(.bold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 3)
                            .background(chartLineColor)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                    }

                    // Time label at bottom
                    PointMark(
                        x: .value("Selected", idx),
                        y: .value("Price", yMin)
                    )
                    .symbol(Circle())
                    .symbolSize(0)
                    .annotation(position: .bottom, spacing: 4) {
                        Text(point.time)
                            .font(.caption2.weight(.medium))
                            .foregroundStyle(AppTheme.Colors.primaryText)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 3)
                            .background(AppTheme.Colors.cardBackground)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 4)
                                    .stroke(AppTheme.Colors.secondaryText.opacity(0.3), lineWidth: 0.5)
                            )
                    }
                }
            }
            .chartXAxis(.hidden)
            .chartYAxis {
                AxisMarks(position: .trailing, values: .automatic(desiredCount: 5)) { value in
                    AxisValueLabel {
                        if let price = value.as(Double.self) {
                            Text(String(format: "%.2f", price))
                                .font(.caption2)
                                .foregroundStyle(AppTheme.Colors.secondaryText)
                        }
                    }
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5, dash: [4, 4]))
                        .foregroundStyle(AppTheme.Colors.secondaryText.opacity(0.2))
                }
            }
            .chartYScale(domain: yMin...yMax)
            .chartXSelection(value: $selectedIndex)
            .chartGesture { proxy in
                DragGesture(minimumDistance: 0)
                    .onChanged { value in
                        if let idx: Int = proxy.value(atX: value.location.x) {
                            selectedIndex = max(0, min(idx, pointCount - 1))
                        }
                    }
                    .onEnded { _ in
                        selectedIndex = nil
                    }
            }
            .frame(height: 280)
            .padding(.vertical, 8)
        }
    }

    // MARK: - Stats

    private var statsGrid: some View {
        let prices = viewModel.chartPoints.map(\.price)
        let high = prices.max() ?? currentPrice
        let low = prices.min() ?? currentPrice
        let open = prices.first ?? currentPrice

        return LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            statCard(title: "开盘", value: String(format: "%.2f", open))
            statCard(title: "最新", value: String(format: "%.2f", currentPrice))
            statCard(title: "最高", value: String(format: "%.2f", high), isHigh: true)
            statCard(title: "最低", value: String(format: "%.2f", low), isLow: true)
        }
    }

    private func statCard(title: String, value: String, isHigh: Bool = false, isLow: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption)
                .foregroundStyle(AppTheme.Colors.secondaryText)
            Text(value)
                .font(.headline.weight(.bold))
                .foregroundStyle(
                    isHigh ? AppTheme.Colors.changeColor(isUp: true) :
                    isLow ? AppTheme.Colors.changeColor(isUp: false) :
                    AppTheme.Colors.primaryText
                )
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .marketCardStyle()
    }
}
