import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct FundDiscoverView: View {
    @Binding var searchText: String
    @State private var searchFilter: SearchFilterType = .all
    
    // Toast
    @State private var showAddedToast = false
    @State private var toastMessage = ""
    @State private var toastType: ToastType = .success
    
    // Group Selection
    @State private var showGroupSelection = false
    @State private var pendingFundToAdd: FundSearchResult?
    
    enum ToastType {
        case success
        case info
        case warning
        
        var icon: String {
            switch self {
            case .success: return "checkmark.circle.fill"
            case .info: return "info.circle.fill"
            case .warning: return "exclamationmark.triangle.fill"
            }
        }
        
        var color: Color {
            switch self {
            case .success: return Color.Alpha.up
            case .info: return Color.Alpha.primary
            case .warning: return Color.Alpha.down
            }
        }
    }
    @State private var viewModel = FundSearchViewModel()
    @State private var watchlistViewModel = FundViewModel()
    @State private var addedFunds = Set<String>()
    @State private var selectedFundToView: FundValuation?
    
    private var filteredResults: [FundSearchResult] {
        switch searchFilter {
        case .all:
            return viewModel.results
        case .stocks:
            return viewModel.results.filter { $0.type == "SH" || $0.type == "SZ" || $0.type == "HK" || $0.type == "US" }
        case .funds:
            return viewModel.results.filter { $0.type != "SH" && $0.type != "SZ" && $0.type != "HK" && $0.type != "US" }
        }
    }

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
                                        Text(LocalizedStringKey("funds.search.recent"))
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
                                        suggestionChip(titleKey: "funds.discover.suggestion.bosera_gold", code: "159937")
                                        suggestionChip(titleKey: "funds.discover.suggestion.huaan_gold", code: "518880")
                                        suggestionChip(titleKey: "funds.discover.suggestion.efund_info", code: "161128")
                                        suggestionChip(titleKey: "funds.discover.suggestion.csi300", code: "510300")
                                        suggestionChip(titleKey: "funds.discover.suggestion.nasdaq100", code: "513100")
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
                    } else {
                        // Picker Filter
                        Section {
                            Picker("", selection: $searchFilter) {
                                ForEach(SearchFilterType.allCases, id: \.self) { filter in
                                    Text(LocalizedStringKey(filter.rawValue))
                                        .tag(filter)
                                }
                            }
                            .pickerStyle(.segmented)
                            .controlSize(.extraLarge)
                            .glassEffect(.regular, in: .capsule)
                            .listRowInsets(EdgeInsets())
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                        }
                    }
                    
                    if viewModel.isLoading {
                        HStack {
                            Spacer()
                            ProgressView().tint(.blue)
                            Spacer()
                        }
                        .listRowBackground(Color.clear)
                    } else if filteredResults.isEmpty && !viewModel.results.isEmpty {
                        VStack(spacing: 12) {
                            Text("funds.search.filters.empty")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
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
                        ForEach(filteredResults) { fund in
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
                                        }
                                    }
                                }
                                .buttonStyle(.plain)
                                
                                Spacer(minLength: 8)
                                
                                // 【核心修复：实时行情感知】展示获取到的实时估值与迷你趋势图
                                if let valuation = viewModel.valuations[fund.code] {
                                    VStack(alignment: .trailing, spacing: 4) {
                                        // 趋势图
                                        if let sparkData = valuation.stats?.sparklineData {
                                            FundSparkline(data: sparkData, isPositive: valuation.estimatedGrowth >= 0)
                                                .frame(width: 50, height: 18)
                                                .opacity(0.8)
                                        }
                                        
                                        Text(String(format: "%+.2f%%", valuation.estimatedGrowth))
                                            .font(.system(size: 14, weight: .bold, design: .rounded))
                                            .foregroundStyle(valuation.estimatedGrowth > 0 ? Color.Alpha.down : (valuation.estimatedGrowth < 0 ? Color.Alpha.up : Color.Alpha.neutral))
                                    }
                                    .padding(.trailing, 4)
                                }
                                
                                LiquidAddButton(isAdded: isAdded) {
                                    if !isAdded {
                                        pendingFundToAdd = fund
                                        showGroupSelection = true
                                    } else {
                                        await performRemove(fund: fund)
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

                // Toast Notification (底部)
                if showAddedToast {
                    VStack {
                        Spacer()
                        HStack(spacing: 8) {
                            Image(systemName: toastType.icon)
                                .foregroundStyle(toastType.color)
                            Text(toastMessage)
                                .foregroundStyle(.primary)
                        }
                        .font(.system(size: 14, weight: .bold))
                        .padding(.vertical, 14)
                        .padding(.horizontal, 24)
                        .glassEffect(.regular, in: .capsule)
                        .clipShape(Capsule())
                        .padding(.bottom, 32)
                    }
                    .transition(.asymmetric(
                        insertion: .move(edge: .bottom).combined(with: .opacity),
                        removal: .move(edge: .bottom).combined(with: .opacity)
                    ))
                }
            }
            .navigationTitle("funds.discover.title")
            .navigationDestination(item: $selectedFundToView) { valuation in
                FundDetailView(valuation: valuation)
            }
            .confirmationDialog(
                String(localized: "funds.group.select_title"),
                isPresented: $showGroupSelection,
                titleVisibility: .visible
            ) {
                Button("funds.group.default") {
                    if let fund = pendingFundToAdd {
                        Task { await performAdd(fund: fund, groupId: nil) }
                    }
                }
                
                ForEach(watchlistViewModel.groups) { group in
                    Button(group.name) {
                        if let fund = pendingFundToAdd {
                            Task { await performAdd(fund: fund, groupId: group.id) }
                        }
                    }
                }
                
                Button("funds.action.cancel", role: .cancel) {
                    pendingFundToAdd = nil
                }
            }

            .onAppear {
                loadRecentSearches()
                Task {
                    await watchlistViewModel.fetchGroups()
                }
            }
        }
    }
    
    // MARK: - Logic

    private func performAdd(fund: FundSearchResult, groupId: String?) async {
        addedFunds.insert(fund.code)
        toastMessage = String(format: String(localized: "app.funds.added_%@"), arguments: [fund.name])
        toastType = .success
        withAnimation(.spring()) { showAddedToast = true }

        saveRecentSearch(code: fund.code, name: fund.name)
        await watchlistViewModel.addFund(code: fund.code, name: fund.name, groupId: groupId)

        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            withAnimation(.easeInOut) { showAddedToast = false }
        }
    }

    private func performRemove(fund: FundSearchResult) async {
        addedFunds.remove(fund.code)
        toastMessage = String(format: String(localized: "app.funds.removed_%@"), arguments: [fund.name])
        toastType = .info
        withAnimation(.spring()) { showAddedToast = true }

        await watchlistViewModel.deleteFund(code: fund.code)

        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            withAnimation(.easeInOut) { showAddedToast = false }
        }
    }
    
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
    @ViewBuilder
    private func suggestionChip(title: String? = nil, titleKey: String? = nil, code: String) -> some View {
        Button {
            searchText = code
        } label: {
            HStack(spacing: 4) {
                if let key = titleKey {
                    Text(LocalizedStringKey(key))
                } else if let t = title {
                    Text(t)
                }
                Text(code)
                    .font(.system(size: 10, design: .monospaced))
                    .opacity(0.6)
            }
            .font(.system(size: 12, weight: .medium))
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .glassEffect(.regular, in: .capsule)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Models

struct FundSearchHistoryItem: Codable, Identifiable, Equatable {
    var id: String { code }
    let code: String
    let name: String
}

enum SearchFilterType: String, CaseIterable {
    case all = "funds.search.filter.all"
    case stocks = "funds.search.filter.stocks"
    case funds = "funds.search.filter.funds"
}

