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
    
    @AppStorage("recent_fund_searches") private var recentSearchesData: Data = Data()
    @State private var recentSearches: [FundSearchHistoryItem] = []
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                List {
                    if searchText.isEmpty {
                        // 最近搜索板块
                        if !recentSearches.isEmpty {
                            Section {
                                VStack(alignment: .leading, spacing: 16) {
                                    HStack {
                                        Text("最近搜索")
                                            .font(.system(size: 14, weight: .bold))
                                            .foregroundStyle(.secondary)
                                        Spacer()
                                        Button {
                                            clearRecentSearches()
                                        } label: {
                                            Image(systemName: "trash")
                                                .font(.system(size: 14))
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                    .padding(.horizontal, 20)
                                    
                                    ScrollView(.horizontal, showsIndicators: false) {
                                        HStack(spacing: 8) {
                                            ForEach(recentSearches) { item in
                                                suggestionChip(title: item.name, code: item.code)
                                            }
                                        }
                                        .padding(.horizontal, 20)
                                    }
                                }
                                .padding(.vertical, 8)
                            }
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                            .listRowInsets(EdgeInsets())
                        }
                        
                        // 热门建议板块
                        Section {
                            VStack(alignment: .leading, spacing: 16) {
                                Text("funds.discover.hot_suggestions")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(.secondary)
                                    .padding(.horizontal, 20)
                                
                                ScrollView(.horizontal, showsIndicators: false) {
                                    HStack(spacing: 8) {
                                        suggestionChip(title: "博时黄金", code: "159937")
                                        suggestionChip(title: "华安黄金", code: "518880")
                                        suggestionChip(title: "易方达信息", code: "161128")
                                        suggestionChip(title: "沪深300", code: "510300")
                                        suggestionChip(title: "纳指100", code: "513100")
                                    }
                                    .padding(.horizontal, 20)
                                }
                                .padding(.bottom, 8)
                            }
                            .padding(.vertical, 8)
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                        .listRowInsets(EdgeInsets())
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
                                    saveRecentSearch(code: fund.code, name: fund.name)
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
                                
                                LiquidAddButton(isAdded: isAdded) {
                                    if !isAdded {
                                        addedFunds.insert(fund.code)
                                        toastMessage = String(localized: "app.funds.added") + " \(fund.name)"
                                        withAnimation(.spring()) { showAddedToast = true }
                                        
                                        saveRecentSearch(code: fund.code, name: fund.name)
                                        await watchlistViewModel.addFund(code: fund.code, name: fund.name)
                                        
                                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                            withAnimation(.easeInOut) { showAddedToast = false }
                                        }
                                    } else {
                                        addedFunds.remove(fund.code)
                                        toastMessage = String(localized: "app.funds.removed") + " \(fund.name)"
                                        withAnimation(.spring()) { showAddedToast = true }
                                        
                                        await watchlistViewModel.deleteFund(code: fund.code)
                                        
                                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                            withAnimation(.easeInOut) { showAddedToast = false }
                                        }
                                    }
                                }
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
                                .foregroundStyle(toastMessage.contains("已取消") ? Color.secondary : Color.green)
                            Text(toastMessage)
                                .foregroundStyle(.primary)
                        }
                        .font(.system(size: 14, weight: .bold))
                        .padding(.vertical, 14)
                        .padding(.horizontal, 24)
                        .glassEffect(.regular, in: .capsule)
                        .clipShape(Capsule())
                        Spacer()
                    }
                    .transition(.scale.combined(with: .opacity))
                }
            }
            .navigationTitle("funds.discover.title")
            .navigationDestination(item: $selectedFundToView) { valuation in
                FundDetailView(valuation: valuation)
            }
            .onAppear {
                loadRecentSearches()
            }
        }
    }
    
    // MARK: - Logic
    
    private func loadRecentSearches() {
        if let decoded = try? JSONDecoder().decode([FundSearchHistoryItem].self, from: recentSearchesData) {
            recentSearches = decoded
        }
    }
    
    private func saveRecentSearch(code: String, name: String) {
        let newItem = FundSearchHistoryItem(code: code, name: name)
        var current = recentSearches
        
        // Remove if exists to bubble it up
        current.removeAll { $0.code == code }
        current.insert(newItem, at: 0)
        
        // Keep only top 10
        if current.count > 10 {
            current = Array(current.prefix(10))
        }
        
        withAnimation {
            recentSearches = current
        }
        
        if let encoded = try? JSONEncoder().encode(current) {
            recentSearchesData = encoded
        }
    }
    
    private func clearRecentSearches() {
        withAnimation {
            recentSearches.removeAll()
        }
        recentSearchesData = Data()
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

// MARK: - Models

struct FundSearchHistoryItem: Codable, Identifiable, Equatable {
    var id: String { code }
    let code: String
    let name: String
}
