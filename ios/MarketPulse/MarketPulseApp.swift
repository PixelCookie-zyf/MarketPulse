import SwiftUI

@main
struct MarketPulseApp: App {
    @StateObject private var viewModel = MarketViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
        }
    }
}
