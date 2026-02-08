import SwiftUI
import AlphaDesign

struct MainTabView: View {
    @State private var selectedTab: Tab = .intelligence
    
    enum Tab: Int {
        case intelligence, funds, backtest, settings
    }
    
    var body: some View {
        TabView(selection: $selectedTab) {
            // Tab 1: Intelligence
            MainDashboardView()
                .tabItem {
                    Label("情报", systemImage: "antenna.radiowaves.left.and.right")
                }
                .tag(Tab.intelligence)
            
            // Tab 2: Funds
            FundDashboardView()
                .tabItem {
                    Label("基金", systemImage: "chart.line.uptrend.xyaxis")
                }
                .tag(Tab.funds)
            
            // Tab 3: Backtest
            BacktestView()
                .tabItem {
                    Label("回测", systemImage: "chart.bar.doc.horizontal.fill")
                }
                .tag(Tab.backtest)
            
            // Tab 4: Settings
            SettingsView()
                .tabItem {
                    Label("个人", systemImage: "person.crop.circle.badge.shield.fill")
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