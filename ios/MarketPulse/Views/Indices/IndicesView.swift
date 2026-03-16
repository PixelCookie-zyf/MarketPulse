import SwiftUI

struct IndicesView: View {
    @EnvironmentObject private var viewModel: MarketViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    ForEach(regions, id: \.title) { region in
                        if !region.items.isEmpty {
                            VStack(alignment: .leading, spacing: 10) {
                                Text(region.title)
                                    .font(.headline)
                                    .foregroundStyle(AppTheme.Colors.primaryText)

                                VStack(spacing: 12) {
                                    ForEach(region.items) { item in
                                        HStack(spacing: 14) {
                                            VStack(alignment: .leading, spacing: 6) {
                                                Text(item.name)
                                                    .font(.headline)
                                                    .foregroundStyle(AppTheme.Colors.primaryText)
                                                Text(item.value, format: .number.precision(.fractionLength(2)))
                                                    .font(.title3.weight(.bold))
                                                    .foregroundStyle(AppTheme.Colors.primaryText)
                                                ChangeLabel(change: item.change, changePct: item.changePct)
                                            }

                                            Spacer()

                                            if !item.sparkline.isEmpty {
                                                SparklineView(data: item.sparkline, isUp: item.isUp)
                                                    .frame(width: 100, height: 48)
                                            }
                                        }
                                    }
                                }
                                .marketCardStyle()
                            }
                        }
                    }
                }
                .padding(16)
            }
            .background(AppTheme.Colors.background.ignoresSafeArea())
            .navigationTitle("全球指数")
            .refreshable {
                await viewModel.loadData()
            }
        }
    }

    private var regions: [(title: String, items: [IndexItem])] {
        [
            ("美股", viewModel.indices.us),
            ("日本", viewModel.indices.jp),
            ("韩国", viewModel.indices.kr),
            ("香港", viewModel.indices.hk),
            ("A股", viewModel.indices.cn)
        ]
    }
}
