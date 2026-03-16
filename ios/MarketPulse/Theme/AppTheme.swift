import SwiftUI

enum AppTheme {
    enum Colors {
        static let background = Color("Background")
        static let cardBackground = Color("CardBackground")
        static let primaryText = Color("PrimaryText")
        static let secondaryText = Color("SecondaryText")
        static let accent = Color("AccentColor")

        static func changeColor(isUp: Bool) -> Color {
            isUp ? Color("UpColor") : Color("DownColor")
        }
    }

    struct CardModifier: ViewModifier {
        @Environment(\.colorScheme) private var colorScheme

        func body(content: Content) -> some View {
            content
                .padding(16)
                .background(Colors.cardBackground)
                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                .shadow(
                    color: colorScheme == .dark ? .clear : .black.opacity(0.08),
                    radius: 14,
                    x: 0,
                    y: 8
                )
        }
    }
}

extension View {
    func marketCardStyle() -> some View {
        modifier(AppTheme.CardModifier())
    }
}
