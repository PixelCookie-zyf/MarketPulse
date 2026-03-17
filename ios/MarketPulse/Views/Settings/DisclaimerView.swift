import SwiftUI

struct DisclaimerView: View {
    var body: some View {
        ScrollView {
            Text("MarketPulse 提供的所有市场数据仅供参考，不构成任何投资建议。数据来源于第三方公开接口，可能存在延迟或误差。用户基于本应用数据做出的任何投资决策，需自行承担风险。\n\nAll market data provided by MarketPulse is for reference only and does not constitute investment advice. Data is sourced from third-party public APIs and may be delayed or inaccurate. Users bear full responsibility for any investment decisions made based on this application's data.")
                .foregroundStyle(AppTheme.Colors.primaryText)
                .padding()
        }
        .background(AppTheme.Colors.background)
        .navigationTitle("免责声明")
        .navigationBarTitleDisplayMode(.inline)
    }
}
