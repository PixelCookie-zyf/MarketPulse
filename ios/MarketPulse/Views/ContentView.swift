import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var viewModel: MarketViewModel

    var body: some View {
        TabView {
            OverviewView()
                .tabItem {
                    Label("总览", systemImage: "chart.bar.doc.horizontal")
                }

            CommodityListView()
                .tabItem {
                    Label("商品", systemImage: "cube.transparent")
                }

            IndicesView()
                .tabItem {
                    Label("指数", systemImage: "chart.line.uptrend.xyaxis")
                }

            SectorsListView()
                .tabItem {
                    Label("板块", systemImage: "square.grid.2x2")
                }
        }
        .tint(AppTheme.Colors.accent)
        .task {
            viewModel.startAutoRefresh()
        }
        .onDisappear {
            viewModel.stopAutoRefresh()
        }
    }
}
