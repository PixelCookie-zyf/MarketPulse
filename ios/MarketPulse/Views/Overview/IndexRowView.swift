import SwiftUI

struct IndexRowView: View {
    let item: IndexItem
    @State private var showChart = false

    var body: some View {
        Button {
            showChart = true
        } label: {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(item.name)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(AppTheme.Colors.primaryText)
                    Text(item.symbol)
                        .font(.caption)
                        .foregroundStyle(AppTheme.Colors.secondaryText)
                }

                Spacer()

                if !item.sparkline.isEmpty {
                    SparklineView(data: item.sparkline, isUp: item.isUp)
                        .frame(width: 84)
                }

                VStack(alignment: .trailing, spacing: 3) {
                    Text(item.value, format: .number.precision(.fractionLength(2)))
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(AppTheme.Colors.primaryText)
                    ChangeLabel(change: item.change, changePct: item.changePct, showAbsoluteValue: false)
                }
            }
            .padding(.vertical, 8)
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $showChart) {
            ChartDetailView(
                symbol: item.symbol,
                name: item.name,
                currentPrice: item.value,
                change: item.change,
                changePct: item.changePct
            )
        }
    }
}
