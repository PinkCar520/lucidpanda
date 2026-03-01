import SwiftUI
import UIKit
import AlphaDesign

struct MainTabView: View {
    @State private var selectedTab: TabValue = .intelligence
    @State private var searchText = "" // 提升搜索状态至根视图以支持 Tab 角色联动
    
    enum TabValue: Hashable {
        case intelligence, funds, backtest, search
    }
    
    var body: some View {
        TabView(selection: $selectedTab) {
            // Tab 1: 信号 (Dashboard)
            Tab("app.tab.intelligence", systemImage: "waveform.path.ecg", value: .intelligence) {
                MainDashboardView()
            }
            .customizationID("intelligence")

            // Tab 2: 基金 (Watchlist)
            Tab("app.tab.funds", systemImage: "star", value: .funds) {
                FundDashboardView()
            }
            .customizationID("funds")

            // Tab 3: 回测 (Strategy)
            Tab("app.tab.backtest", systemImage: "clock.arrow.circlepath", value: .backtest) {
                BacktestView()
            }
            .customizationID("backtest")

            // Tab 4: 搜索 (独立的搜索角色 Tab)
            Tab("app.tab.search", systemImage: "magnifyingglass", value: .search, role: .search) {
                FundDiscoverView(searchText: $searchText)
                    .searchable(text: $searchText, placement: .navigationBarDrawer(displayMode: .always),prompt: Text("app.search.fund_prompt"))
            }
            .customizationID("search")
        }
        .symbolVariant(.fill)
        .onChange(of: selectedTab) { old, newValue in
            let generator = UIImpactFeedbackGenerator(style: .soft)
            generator.prepare()
            generator.impactOccurred()
        }
    }
}

#Preview {
    MainTabView()
        .environment(AppRootViewModel())
}
