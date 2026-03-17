import SwiftUI

struct CommodityListView: View {
    @EnvironmentObject private var viewModel: MarketViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    ForEach(viewModel.commodities) { item in
                        CommodityListRow(item: item)
                    }
                }
                .padding(16)
            }
            .background(AppTheme.Colors.background.ignoresSafeArea())
            .navigationTitle("大宗商品")
            .refreshable {
                await viewModel.loadData()
            }
        }
    }
}

private struct CommodityListRow: View {
    let item: CommodityItem
    @State private var showChart = false

    var body: some View {
        Button {
            showChart = true
        } label: {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(item.name)
                            .font(.title3.weight(.bold))
                            .foregroundStyle(AppTheme.Colors.primaryText)
                        Text(item.nameEn)
                            .font(.caption)
                            .foregroundStyle(AppTheme.Colors.secondaryText)
                    }

                    Spacer()

                    VStack(alignment: .trailing, spacing: 4) {
                        Text(item.safePrice, format: .number.precision(.fractionLength(2)))
                            .font(.title2.weight(.bold))
                            .foregroundStyle(AppTheme.Colors.primaryText)
                        ChangeLabel(change: item.safeChange, changePct: item.safeChangePct)
                    }
                }

                Divider()

                HStack {
                    detailMetric(title: "最高", value: item.safeHigh)
                    Spacer()
                    detailMetric(title: "最低", value: item.safeLow)
                    Spacer()
                    VStack(alignment: .leading, spacing: 4) {
                        Text("单位")
                            .font(.caption)
                            .foregroundStyle(AppTheme.Colors.secondaryText)
                        Text(item.unit)
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(AppTheme.Colors.primaryText)
                    }
                }
            }
            .marketCardStyle()
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $showChart) {
            ChartDetailView(
                symbol: item.symbol,
                name: item.name,
                currentPrice: item.safePrice,
                change: item.safeChange,
                changePct: item.safeChangePct
            )
        }
    }

    private func detailMetric(title: String, value: Double) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(AppTheme.Colors.secondaryText)
            Text(value, format: .number.precision(.fractionLength(2)))
                .font(.subheadline.weight(.medium))
                .foregroundStyle(AppTheme.Colors.primaryText)
        }
    }
}
