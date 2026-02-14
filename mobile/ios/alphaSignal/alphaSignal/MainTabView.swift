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
            Tab("信号", systemImage: "antenna.radiowaves.left.and.right", value: .intelligence) {
                MainDashboardView()
            }
            
            // Tab 2: 基金 (Watchlist)
            Tab("基金", systemImage: "chart.line.uptrend.xyaxis", value: .funds) {
                FundDashboardView()
            }
            
            // Tab 3: 回测 (Strategy)
            Tab("回测", systemImage: "chart.bar.doc.horizontal.fill", value: .backtest) {
                BacktestView()
            }
            
            // Tab 4: 搜索 (独立的搜索角色 Tab)
            Tab("搜索", systemImage: "magnifyingglass", value: .search, role: .search) {
                FundDiscoverView(searchText: $searchText)
                    .searchable(text: $searchText, prompt: "搜索基金代码或名称")
            }
        }
    }
}

#Preview {
    MainTabView()
        .environment(AppRootViewModel())
}
