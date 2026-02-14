import SwiftUI
import AlphaDesign

struct MainTabView: View {
    @State private var selectedTab: Tab = .intelligence
    
    enum Tab: Int {
        case intelligence, funds, backtest, settings
    }
    
    var body: some View {
        TabView(selection: $selectedTab) {
            // Tab 1: Gold Tracking
            MainDashboardView()
                .tabItem {
                    Label("黄金跟踪", systemImage: "antenna.radiowaves.left.and.right")
                }
                .tag(Tab.intelligence)
            
            // Tab 2: ALPHA Funds
            FundDashboardView()
                .tabItem {
                    Label("ALPHA基金", systemImage: "chart.line.uptrend.xyaxis")
                }
                .tag(Tab.funds)
            
            // Tab 3: Strategy Backtest
            BacktestView()
                .tabItem {
                    Label("策略回测", systemImage: "chart.bar.doc.horizontal.fill")
                }
                .tag(Tab.backtest)
            
            // Tab 4: Recon Monitoring
            ReconciliationView()
                .tabItem {
                    Label("对账监控", systemImage: "checkmark.shield.fill")
                }
                .tag(Tab.settings)
        }
        // Note: In Xcode 26 / iOS 19+, the .tabViewStyle(.sidebarAdaptable) or 
        // default styles automatically render with the 'Liquid Glass' material
        // when placed over a rich background like our LiquidBackground().
    }
}

#Preview {
    MainTabView()
        .environment(AppRootViewModel())
}