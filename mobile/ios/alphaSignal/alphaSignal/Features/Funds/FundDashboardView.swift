import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct FundDashboardView: View {
    @State private var viewModel = FundViewModel()
    @State private var showSearch = false
    @Environment(\.colorScheme) var colorScheme
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 24) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("AlphaFunds 估值")
                                    .font(.system(size: 24, weight: .black, design: .rounded))
                                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                                Text("实时持仓穿透与净值精算")
                                    .font(.caption2)
                                    .foregroundStyle(.gray)
                            }
                            Spacer()
                            
                            HStack(spacing: 12) {
                                Button {
                                    showSearch.toggle()
                                } label: {
                                    Image(systemName: "plus")
                                        .font(.system(size: 16, weight: .bold))
                                        .foregroundStyle(.blue)
                                        .padding(10)
                                        .background(.blue.opacity(0.1))
                                        .clipShape(Circle())
                                }
                                
                                Button {
                                    Task { await viewModel.fetchWatchlist() }
                                } label: {
                                    Image(systemName: "arrow.clockwise")
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(.gray)
                                }
                            }
                        }
                        .padding(.horizontal)
                        .padding(.top, 24)
                        
                        if viewModel.watchlist.isEmpty {
                            emptyStateView
                        } else {
                            VStack(spacing: 16) {
                                ForEach(viewModel.watchlist) { valuation in
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
                }
            }
            .sheet(isPresented: $showSearch) {
                FundSearchView { selectedFund in
                    Task { await viewModel.addFund(code: selectedFund.code, name: selectedFund.name) }
                }
            }
        }
        .task {
            await viewModel.fetchWatchlist()
        }
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Spacer(minLength: 100)
            Image(systemName: "chart.line.uptrend.xyaxis")
                .font(.system(size: 48))
                .foregroundStyle(.gray.opacity(0.2))
            Text("您的自选库为空")
                .font(.headline)
                .foregroundStyle(.gray)
            Button("添加第一只基金") { showSearch = true }
                .font(.subheadline.bold())
                .foregroundStyle(.blue)
        }
    }
}
