import SwiftUI

@main
struct MarketPulseApp: App {
    @StateObject private var viewModel = MarketViewModel()
    @StateObject private var appSettings = AppSettings()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
                .environmentObject(appSettings)
                .preferredColorScheme(appSettings.appTheme.colorScheme)
        }
    }
}
