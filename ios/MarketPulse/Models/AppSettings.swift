import SwiftUI

@MainActor
final class AppSettings: ObservableObject {
    @AppStorage("appTheme") var appTheme: AppThemeMode = .system
    @AppStorage("appLanguage") var appLanguage: AppLanguage = .chinese
    @AppStorage("currencyUnit") var currencyUnit: CurrencyUnit = .usd
    @AppStorage("priceAlertEnabled") var priceAlertEnabled: Bool = false
    @AppStorage("priceAlertThreshold") var priceAlertThreshold: Double = 3.0
}

// MARK: - Theme Mode

enum AppThemeMode: String, CaseIterable, Codable {
    case system = "system"
    case dark = "dark"
    case light = "light"

    var displayName: String {
        switch self {
        case .system: "跟随系统"
        case .dark: "深色"
        case .light: "浅色"
        }
    }

    var colorScheme: ColorScheme? {
        switch self {
        case .system: nil
        case .dark: .dark
        case .light: .light
        }
    }
}

// MARK: - Language

enum AppLanguage: String, CaseIterable, Codable {
    case chinese = "zh"
    case english = "en"

    var displayName: String {
        switch self {
        case .chinese: "中文"
        case .english: "English"
        }
    }
}

// MARK: - Currency Unit

enum CurrencyUnit: String, CaseIterable, Codable {
    case usd = "USD"
    case cny = "CNY"

    var symbol: String {
        switch self {
        case .usd: "$"
        case .cny: "¥"
        }
    }
}
