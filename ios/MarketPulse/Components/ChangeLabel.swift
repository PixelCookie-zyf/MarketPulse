import SwiftUI

struct ChangeLabel: View {
    let change: Double
    let changePct: Double
    var showAbsoluteValue = true

    private var isUp: Bool { change >= 0 }
    private var arrow: String { isUp ? "▲" : "▼" }

    var body: some View {
        HStack(spacing: 4) {
            if showAbsoluteValue {
                Text("\(arrow) \(abs(change), specifier: "%.2f")")
            }
            Text("\(changePct, specifier: "%+.2f")%")
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(AppTheme.Colors.changeColor(isUp: isUp))
    }
}
