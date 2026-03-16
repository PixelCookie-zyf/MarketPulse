import Charts
import SwiftUI

func normalizeSparklineData(_ data: [Double], padding: Double = 0.08) -> [Double] {
    guard let minValue = data.min(), let maxValue = data.max(), !data.isEmpty else {
        return []
    }

    let safePadding = min(max(padding, 0), 0.45)
    let usableHeight = 1 - (safePadding * 2)
    let range = maxValue - minValue

    if range <= .ulpOfOne {
        return Array(repeating: 0.5, count: data.count)
    }

    return data.map { value in
        safePadding + ((value - minValue) / range) * usableHeight
    }
}

struct SparklineView: View {
    let data: [Double]
    let isUp: Bool

    var body: some View {
        if !data.isEmpty {
            let normalizedData = normalizeSparklineData(data)

            Chart(Array(normalizedData.enumerated()), id: \.offset) { index, value in
                AreaMark(
                    x: .value("Index", index),
                    yStart: .value("Baseline", 0),
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
            .chartYScale(domain: 0...1)
            .frame(height: 36)
        }
    }
}
