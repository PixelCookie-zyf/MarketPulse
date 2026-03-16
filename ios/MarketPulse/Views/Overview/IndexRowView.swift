import SwiftUI

struct IndexRowView: View {
    let item: IndexItem

    var body: some View {
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
}
