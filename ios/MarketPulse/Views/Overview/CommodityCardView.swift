import SwiftUI

struct CommodityCardView: View {
    let item: CommodityItem

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.name)
                        .font(.headline)
                        .foregroundStyle(AppTheme.Colors.primaryText)
                    Text(item.nameEn)
                        .font(.caption)
                        .foregroundStyle(AppTheme.Colors.secondaryText)
                }
                Spacer()
                Text(item.unit)
                    .font(.caption2)
                    .foregroundStyle(AppTheme.Colors.secondaryText)
            }

            Text(item.price, format: .number.precision(.fractionLength(2)))
                .font(.title2.weight(.bold))
                .foregroundStyle(AppTheme.Colors.primaryText)

            ChangeLabel(change: item.change, changePct: item.changePct)

            HStack {
                stat("高", value: item.high)
                Spacer()
                stat("低", value: item.low)
            }
        }
        .marketCardStyle()
    }

    private func stat(_ label: String, value: Double) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(AppTheme.Colors.secondaryText)
            Text(value, format: .number.precision(.fractionLength(2)))
                .font(.footnote.weight(.medium))
                .foregroundStyle(AppTheme.Colors.primaryText)
        }
    }
}
