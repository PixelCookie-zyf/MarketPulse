import Charts
import SwiftUI

struct SparklineView: View {
    let data: [Double]
    let isUp: Bool

    var body: some View {
        if data.isEmpty {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(AppTheme.Colors.background.opacity(0.6))
                .frame(height: 36)
        } else {
            Chart(Array(data.enumerated()), id: \.offset) { index, value in
                AreaMark(
                    x: .value("Index", index),
                    yStart: .value("Baseline", data.min() ?? 0),
                    yEnd: .value("Value", value)
                )
                .foregroundStyle(
                    LinearGradient(
                        colors: [
                            AppTheme.Colors.changeColor(isUp: isUp).opacity(0.28),
                            AppTheme.Colors.changeColor(isUp: isUp).opacity(0.04)
                        ],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )

                LineMark(
                    x: .value("Index", index),
                    y: .value("Value", value)
                )
                .foregroundStyle(AppTheme.Colors.changeColor(isUp: isUp))
                .interpolationMethod(.catmullRom)
                .lineStyle(.init(lineWidth: 2))
            }
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .chartLegend(.hidden)
            .frame(height: 36)
        }
    }
}
