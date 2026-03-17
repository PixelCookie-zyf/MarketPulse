import SwiftUI

// MARK: - AppTheme

enum AppTheme {

    // MARK: - Colors

    enum Colors {
        // Existing asset-catalog colors (backward compatible)
        static let background = Color("Background")
        static let cardBackground = Color("CardBackground")
        static let primaryText = Color("PrimaryText")
        static let secondaryText = Color("SecondaryText")
        static let accent = Color("AccentColor")

        // Premium gold / accent
        static let gold = Color(light: Color(hex: 0xD4A017), dark: Color(hex: 0xF0B90B))

        // Semantic change colors
        static let upColor = Color("UpColor")
        static let downColor = Color("DownColor")

        static func changeColor(isUp: Bool) -> Color {
            isUp ? upColor : downColor
        }
    }

    // MARK: - Spacing

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 20
        static let xxl: CGFloat = 24
    }

    // MARK: - Font helpers

    enum Font {
        static func regular(_ size: CGFloat) -> SwiftUI.Font {
            .system(size: size, weight: .regular)
        }

        static func medium(_ size: CGFloat) -> SwiftUI.Font {
            .system(size: size, weight: .medium)
        }

        static func semibold(_ size: CGFloat) -> SwiftUI.Font {
            .system(size: size, weight: .semibold)
        }

        static func bold(_ size: CGFloat) -> SwiftUI.Font {
            .system(size: size, weight: .bold)
        }

        static func heavy(_ size: CGFloat) -> SwiftUI.Font {
            .system(size: size, weight: .heavy)
        }

        // Pre-defined sizes
        static let caption = regular(11)
        static let footnote = regular(13)
        static let body = regular(15)
        static let headline = semibold(17)
        static let title3 = semibold(20)
        static let title2 = bold(22)
        static let title1 = bold(28)
        static let largeTitle = bold(34)
    }

    // MARK: - Card Modifier (premium glass-morphism)

    struct CardModifier: ViewModifier {
        @Environment(\.colorScheme) private var colorScheme

        func body(content: Content) -> some View {
            content
                .padding(Spacing.lg)
                .background(cardBackground)
                .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                .overlay(cardBorder)
                .shadow(
                    color: colorScheme == .dark ? .clear : .black.opacity(0.08),
                    radius: 16,
                    x: 0,
                    y: 4
                )
        }

        @ViewBuilder
        private var cardBackground: some View {
            if colorScheme == .dark {
                Color.white.opacity(0.06)
            } else {
                Color.white
            }
        }

        @ViewBuilder
        private var cardBorder: some View {
            if colorScheme == .dark {
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
            }
        }
    }

    // MARK: - Glow Modifier

    struct GlowModifier: ViewModifier {
        let isUp: Bool
        var intensity: CGFloat = 0.45
        var radius: CGFloat = 8

        private var glowColor: Color {
            isUp ? Colors.upColor : Colors.downColor
        }

        func body(content: Content) -> some View {
            content
                .background(
                    glowColor
                        .opacity(intensity)
                        .blur(radius: radius)
                        .scaleEffect(1.3)
                )
        }
    }

    // MARK: - Staggered Animation Modifier

    struct StaggeredAnimationModifier: ViewModifier {
        let index: Int
        var baseDelay: Double = 0.05

        @State private var appeared = false

        func body(content: Content) -> some View {
            content
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 12)
                .onAppear {
                    withAnimation(
                        .easeOut(duration: 0.35)
                        .delay(Double(index) * baseDelay)
                    ) {
                        appeared = true
                    }
                }
        }
    }
}

// MARK: - View Extensions

extension View {
    /// Backward-compatible premium card style.
    func marketCardStyle() -> some View {
        modifier(AppTheme.CardModifier())
    }

    /// Subtle color glow behind change labels.
    func changeGlow(isUp: Bool, intensity: CGFloat = 0.45, radius: CGFloat = 8) -> some View {
        modifier(AppTheme.GlowModifier(isUp: isUp, intensity: intensity, radius: radius))
    }

    /// Fade-in with upward slide, staggered by index.
    func staggeredAppear(index: Int, baseDelay: Double = 0.05) -> some View {
        modifier(AppTheme.StaggeredAnimationModifier(index: index, baseDelay: baseDelay))
    }
}

// MARK: - Color Helpers

extension Color {
    /// Create a Color from a hex integer (e.g. 0xF0B90B).
    init(hex: UInt, opacity: Double = 1.0) {
        self.init(
            red: Double((hex >> 16) & 0xFF) / 255.0,
            green: Double((hex >> 8) & 0xFF) / 255.0,
            blue: Double(hex & 0xFF) / 255.0,
            opacity: opacity
        )
    }

    /// Adaptive color that switches between light and dark variants.
    init(light: Color, dark: Color) {
        self.init(uiColor: UIColor { traits in
            traits.userInterfaceStyle == .dark
                ? UIColor(dark)
                : UIColor(light)
        })
    }
}
