import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct FundDashboardView: View {
    @State private var viewModel = FundViewModel()
    @Environment(\.colorScheme) var colorScheme
    
    var body: some View {
        @Bindable var viewModel = viewModel
        return NavigationStack {
            ZStack {
                LiquidBackground()
                
                VStack(spacing: 0) {
                    // 1. 顶部状态与操作
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("funds.title")
                                    .font(.system(size: 24, weight: .black, design: .rounded))
                                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                                Text("funds.subtitle")
                                    .font(.caption2)
                                    .foregroundStyle(.gray)
                            }
                            Spacer()
                            
                            HStack(spacing: 16) {
                                // 排序切换按钮 (对齐视觉语义)
                                Button {
                                    withAnimation(.spring()) {
                                        viewModel.toggleSortOrder()
                                    }
                                } label: {
                                    Image(systemName: sortIcon)
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(viewModel.sortOrder == .none ? .gray : .blue)
                                }
                                
                                // 刷新按钮
                                Button {
                                    Task { await viewModel.fetchWatchlist() }
                                } label: {
                                    Image(systemName: "arrow.clockwise")
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(.gray)
                                }
                            }
                        }
                        

                    }
                    .padding(.horizontal)
                    .padding(.top, 24)
                    .padding(.bottom, 12)
                    
                    ScrollView(showsIndicators: false) {
                        VStack(spacing: 16) {
                            if viewModel.watchlist.isEmpty && !viewModel.isLoading {
                                emptyStateView
                            } else {
                                VStack(spacing: 16) {
                                    ForEach(viewModel.sortedWatchlist) { valuation in
                                        NavigationLink(destination: FundDetailView(valuation: valuation)) {
                                            FundCompactCard(valuation: valuation)
                                        }
                                        .buttonStyle(.plain)
                                    }
                                }
                                .padding(.horizontal)
                            }
                            
                            Spacer(minLength: 100)
                        }
                        .padding(.top, 12)
                    }
                }
            }
        }
        .task {
            await viewModel.fetchWatchlist()
        }
    }
    
    private var sortIcon: String {
        switch viewModel.sortOrder {
        case .none: return "arrow.up.arrow.down"
        case .highGrowthFirst: return "arrow.up.circle.fill"
        case .highDropFirst: return "arrow.down.circle.fill"
        }
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Spacer(minLength: 100)
            Image(systemName: "chart.line.uptrend.xyaxis")
                .font(.system(size: 48))
                .foregroundStyle(.gray.opacity(0.2))
            Text("funds.empty.title")
                .font(.headline)
                .foregroundStyle(.gray)
            Text("funds.empty.hint")
                .font(.subheadline)
                .foregroundStyle(.blue)
        }
    }
}
