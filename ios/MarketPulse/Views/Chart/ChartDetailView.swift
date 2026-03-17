import SwiftUI
import Charts

struct ChartDetailView: View {
    @StateObject private var viewModel: ChartViewModel
    @Environment(\.dismiss) private var dismiss

    let currentPrice: Double
    let change: Double
    let changePct: Double

    init(symbol: String, name: String, currentPrice: Double, change: Double, changePct: Double) {
        _viewModel = StateObject(wrappedValue: ChartViewModel(symbol: symbol, name: name))
        self.currentPrice = currentPrice
        self.change = change
        self.changePct = changePct
    }

    private var isUp: Bool { change >= 0 }
    private var accentColor: Color { AppTheme.Colors.changeColor(isUp: isUp) }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Price header
                    priceHeader

                    // Period selector
                    periodPicker

                    // Chart
                    chartView

                    // Stats grid
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

    private var priceHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(String(format: "%.2f", currentPrice))
                .font(.system(size: 40, weight: .heavy, design: .rounded))
                .foregroundStyle(AppTheme.Colors.primaryText)
                .contentTransition(.numericText())

            HStack(spacing: 8) {
                Text(String(format: "%+.2f", change))
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(accentColor)

                Text(String(format: "(%+.2f%%)", changePct))
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(accentColor)
            }
            .shadow(color: accentColor.opacity(0.3), radius: 4)
        }
    }

    private var periodPicker: some View {
        HStack(spacing: 0) {
            ForEach(ChartViewModel.ChartPeriod.allCases, id: \.self) { period in
                Button {
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
                                ? accentColor.opacity(0.15)
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
            Chart {
                ForEach(Array(viewModel.chartPoints.enumerated()), id: \.offset) { index, point in
                    LineMark(
                        x: .value("Time", index),
                        y: .value("Price", point.price)
                    )
                    .foregroundStyle(accentColor)
                    .lineStyle(StrokeStyle(lineWidth: 2))
                    .interpolationMethod(.catmullRom)

                    AreaMark(
                        x: .value("Time", index),
                        y: .value("Price", point.price)
                    )
                    .foregroundStyle(
                        LinearGradient(
                            colors: [accentColor.opacity(0.2), accentColor.opacity(0.02)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .interpolationMethod(.catmullRom)
                }
            }
            .chartXAxis(.hidden)
            .chartYAxis {
                AxisMarks(position: .trailing) { value in
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
            .chartYScale(domain: .automatic(includesZero: false))
            .frame(height: 280)
            .padding(.vertical, 8)
        }
    }

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
