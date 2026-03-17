import SwiftUI

struct CommodityCardView: View {
    let item: CommodityItem

    private var accentColor: Color {
        AppTheme.Colors.changeColor(isUp: item.isUp)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Colored accent line at the top
            accentColor
                .frame(height: 2)
                .frame(maxWidth: .infinity)

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
                    .font(.title.weight(.heavy))
                    .foregroundStyle(AppTheme.Colors.primaryText)
                    .contentTransition(.numericText())

                ChangeLabel(change: item.change, changePct: item.changePct)

                HStack {
                    stat("高", value: item.high)
                    Spacer()
                    stat("低", value: item.low)
                }
            }
            .padding(AppTheme.Spacing.lg)
        }
        .background(
            LinearGradient(
                colors: [
                    accentColor.opacity(0.03),
                    Color.clear
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        )
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .stroke(
                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.10),
                            Color.white.opacity(0.03)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 1
                )
        )
        .shadow(
            color: .black.opacity(0.08),
            radius: 16,
            x: 0,
            y: 4
        )
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
