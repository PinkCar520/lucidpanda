import SwiftUI
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

            // Tab 2: 基金 (Watchlist)
            Tab("app.tab.funds", systemImage: "chart.pie", value: .funds) {
                FundDashboardView()
            }

            // Tab 3: 回测 (Strategy)
            Tab("app.tab.backtest", systemImage: "clock.arrow.circlepath", value: .backtest) {
                BacktestView()
            }

            // Tab 4: 搜索 (独立的搜索角色 Tab)
            Tab("app.tab.search", systemImage: "magnifyingglass", value: .search, role: .search) {
                FundDiscoverView(searchText: $searchText)
                    .searchable(text: $searchText, prompt: Text("app.search.fund_prompt"))
            }
        }
    }
}

#Preview {
    MainTabView()
        .environment(AppRootViewModel())
}
