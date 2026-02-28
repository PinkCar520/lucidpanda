import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct FundDiscoverView: View {
    @Binding var searchText: String
    @State private var viewModel = FundSearchViewModel()
    @State private var watchlistViewModel = FundViewModel()
    @State private var showAddedToast = false
    @State private var toastMessage = ""
    @State private var addedFunds = Set<String>()
    @State private var selectedFundToView: FundValuation?
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                List {
                    if searchText.isEmpty {
                        // 热门建议板块
                        Section {
                            VStack(alignment: .leading, spacing: 16) {
                                Text("funds.discover.hot_suggestions")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(.secondary)
                                
                                ScrollView(.horizontal, showsIndicators: false) {
                                    HStack(spacing: 8) {
                                        suggestionChip(title: "博时黄金", code: "159937")
                                        suggestionChip(title: "华安黄金", code: "518880")
                                        suggestionChip(title: "易方达信息", code: "161128")
                                        suggestionChip(title: "沪深300", code: "510300")
                                        suggestionChip(title: "纳指100", code: "513100")
                                    }
                                }
                            }
                            .padding(.vertical, 8)
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    }
                    
                    if viewModel.isLoading {
                        HStack {
                            Spacer()
                            ProgressView().tint(.blue)
                            Spacer()
                        }
                        .listRowBackground(Color.clear)
                    } else if viewModel.results.isEmpty && searchText.count >= 2 {
                        VStack(spacing: 12) {
                            Image(systemName: "doc.text.magnifyingglass")
                                .font(.largeTitle)
                                .foregroundStyle(.gray.opacity(0.3))
                            Text("funds.search.not_found")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                        .listRowBackground(Color.clear)
                    } else {
                        ForEach(viewModel.results) { fund in
                            let isAdded = addedFunds.contains(fund.code)
                            
                            HStack(spacing: 12) {
                                Button {
                                    let dummyValuation = FundValuation(
                                        fundCode: fund.code,
                                        fundName: fund.name,
                                        estimatedGrowth: 0,
                                        totalWeight: 0,
                                        components: [],
                                        timestamp: Date(),
                                        stats: nil
                                    )
                                    selectedFundToView = dummyValuation
                                } label: {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text(fund.name)
                                            .font(.system(size: 16, weight: .bold))
                                            .foregroundStyle(isAdded ? Color.secondary : Color.primary)
                                            .lineLimit(1)
                                        
                                        HStack(spacing: 6) {
                                            Text(fund.code)
                                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                                .foregroundStyle(.secondary)
                                                .padding(.horizontal, 6)
                                                .padding(.vertical, 2)
                                                .background(Color(uiColor: .tertiarySystemFill))
                                                .clipShape(RoundedRectangle(cornerRadius: 6))
                                                
                                            if let type = fund.type, !type.isEmpty {
                                                Text(type)
                                                    .font(.system(size: 10, weight: .semibold))
                                                    .foregroundStyle(isAdded ? .gray : .blue)
                                                    .padding(.horizontal, 5)
                                                    .padding(.vertical, 2)
                                                    .background(isAdded ? Color.gray.opacity(0.1) : Color.blue.opacity(0.1))
                                                    .clipShape(RoundedRectangle(cornerRadius: 4))
                                            }
                                            
                                            Text(fund.company ?? String(localized: "funds.company.unknown"))
                                                .font(.system(size: 11))
                                                .foregroundStyle(.gray)
                                        }
                                    }
                                }
                                .buttonStyle(.plain)
                                
                                Spacer(minLength: 16)
                                
                                Button {
                                    if !isAdded {
                                        Task {
                                            await watchlistViewModel.addFund(code: fund.code, name: fund.name)
                                            addedFunds.insert(fund.code)
                                            toastMessage = "已添加 \(fund.name)"
                                            withAnimation(.spring()) { showAddedToast = true }
                                            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                                withAnimation(.easeInOut) { showAddedToast = false }
                                            }
                                        }
                                    } else {
                                        Task {
                                            await watchlistViewModel.deleteFund(code: fund.code)
                                            addedFunds.remove(fund.code)
                                            toastMessage = "已取消 \(fund.name)"
                                            withAnimation(.spring()) { showAddedToast = true }
                                            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                                withAnimation(.easeInOut) { showAddedToast = false }
                                            }
                                        }
                                    }
                                } label: {
                                    if isAdded {
                                        Image(systemName: "checkmark.circle.fill")
                                            .font(.system(size: 22))
                                            .foregroundStyle(.green)
                                            .symbolRenderingMode(.hierarchical)
                                    } else {
                                        Image(systemName: "plus.circle.fill")
                                            .font(.system(size: 22))
                                            .foregroundStyle(.blue)
                                            .symbolRenderingMode(.hierarchical)
                                    }
                                }
                                .buttonStyle(.plain)
                            }
                            .padding(.vertical, 8)
                            .padding(.horizontal, 4)
                            .listRowBackground(Color(uiColor: .systemBackground))
                        }
                    }
                }
                .scrollContentBackground(.hidden)
                // 注意：.searchable 已经在 MainTabView 层级挂载，这里响应 searchText 的变化
                .onChange(of: searchText) {
                    viewModel.query = searchText
                    Task { await viewModel.performSearch() }
                }
                
                // Toast Notification (Centered)
                if showAddedToast {
                    VStack {
                        Spacer()
                        HStack {
                            Image(systemName: toastMessage.contains("已取消") ? "xmark.circle.fill" : "checkmark.circle.fill")
                            Text(toastMessage)
                        }
                        .font(.system(size: 14, weight: .bold))
                        .padding(.vertical, 14)
                        .padding(.horizontal, 24)
                        // Make it slightly dark translucent
                        .background(.ultraThinMaterial)
                        .colorScheme(.dark)
                        .clipShape(Capsule())
                        .shadow(color: .black.opacity(0.15), radius: 20, x: 0, y: 10)
                        Spacer()
                    }
                    .transition(.scale.combined(with: .opacity))
                }
            }
            .navigationTitle("funds.discover.title")
            .navigationDestination(item: $selectedFundToView) { valuation in
                FundDetailView(valuation: valuation)
            }
        }
    }
    
    private func suggestionChip(title: String, code: String) -> some View {
        Button {
            searchText = code
        } label: {
            Text(title)
                .font(.system(size: 14, weight: .bold))
                .padding(.horizontal, 20)
                .padding(.vertical, 10)
                .foregroundStyle(.blue)
                .glassEffect(.regular, in: .capsule)
                .clipShape(Capsule())
        }
    }
}
