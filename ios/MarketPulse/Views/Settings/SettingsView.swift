import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appSettings: AppSettings

    var body: some View {
        NavigationStack {
            List {
                appearanceSection
                dataSection
                notificationSection
                aboutSection
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
            .background(AppTheme.Colors.background)
            .navigationTitle("设置")
        }
    }

    // MARK: - Appearance

    private var appearanceSection: some View {
        Section {
            Picker("主题", selection: $appSettings.appTheme) {
                ForEach(AppThemeMode.allCases, id: \.self) { mode in
                    Text(mode.displayName).tag(mode)
                }
            }
            .pickerStyle(.segmented)

            Picker("语言", selection: $appSettings.appLanguage) {
                ForEach(AppLanguage.allCases, id: \.self) { lang in
                    Text(lang.displayName).tag(lang)
                }
            }
        } header: {
            Text("外观")
                .foregroundStyle(AppTheme.Colors.secondaryText)
        }
    }

    // MARK: - Data

    private var dataSection: some View {
        Section {
            Picker("货币单位", selection: $appSettings.currencyUnit) {
                ForEach(CurrencyUnit.allCases, id: \.self) { unit in
                    Text("\(unit.symbol) \(unit.rawValue)").tag(unit)
                }
            }
        } header: {
            Text("数据")
                .foregroundStyle(AppTheme.Colors.secondaryText)
        }
    }

    // MARK: - Notifications

    private var notificationSection: some View {
        Section {
            Toggle("价格提醒", isOn: $appSettings.priceAlertEnabled)
                .tint(AppTheme.Colors.accent)

            if appSettings.priceAlertEnabled {
                VStack(alignment: .leading, spacing: 8) {
                    Text("涨跌幅阈值: \(appSettings.priceAlertThreshold, specifier: "%.0f")%")
                        .foregroundStyle(AppTheme.Colors.primaryText)
                    Slider(
                        value: $appSettings.priceAlertThreshold,
                        in: 1...10,
                        step: 1
                    )
                    .tint(AppTheme.Colors.accent)
                }
            }
        } header: {
            Text("通知")
                .foregroundStyle(AppTheme.Colors.secondaryText)
        }
    }

    // MARK: - About

    private var aboutSection: some View {
        Section {
            HStack {
                Text("版本")
                Spacer()
                Text("1.0.0")
                    .foregroundStyle(AppTheme.Colors.secondaryText)
            }

            NavigationLink("数据源") {
                DataSourcesView()
            }

            NavigationLink("免责声明") {
                DisclaimerView()
            }
        } header: {
            Text("关于")
                .foregroundStyle(AppTheme.Colors.secondaryText)
        }
    }
}

// MARK: - Data Sources View

private struct DataSourcesView: View {
    var body: some View {
        List {
            Text("AKShare")
            Text("Stooq")
            Text("GoldAPI")
            Text("Alpha Vantage")
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
        .background(AppTheme.Colors.background)
        .navigationTitle("数据源")
        .navigationBarTitleDisplayMode(.inline)
    }
}
