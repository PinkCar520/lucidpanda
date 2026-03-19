import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct FundDiscoverView: View {
    @Binding var searchText: String
    @State private var searchFilter: SearchFilterType = .all
    
    // UI State
    @State private var viewModel = FundSearchViewModel()
    @State private var watchlistViewModel = FundViewModel()
    @State private var addedFunds = Set<String>()
    @State private var selectedFundToView: FundValuation?
    
    // Toast
    enum ToastType {
        case success, info, warning
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
    
    @State private var showAddedToast = false
    @State private var toastMessage = ""
    @State private var toastType: ToastType = .success
    
    // Group Selection
    @State private var showGroupSelection = false
    @State private var pendingFundToAdd: FundSearchResult?

    @AppStorage("recent_fund_searches") private var recentSearchesData: Data = Data()
    @State private var recentSearches: [FundSearchHistoryItem] = []
    
    // MARK: - Theme Constants
    private struct TaupeTheme {
        static let background = Color(red: 12/255, green: 10/255, blue: 9/255)
        static let primary = Color(red: 179/255, green: 89/255, blue: 25/255)
        static let taupe100 = Color(red: 231/255, green: 229/255, blue: 228/255)
        static let taupe200 = Color(red: 214/255, green: 211/255, blue: 209/255)
        static let taupe300 = Color(red: 168/255, green: 162/255, blue: 158/255)
        static let taupe400 = Color(red: 120/255, green: 113/255, blue: 108/255)
        static let taupe500 = Color(red: 87/255, green: 83/255, blue: 78/255)
        static let taupe600 = Color(red: 68/255, green: 64/255, blue: 60/255)
        static let taupe700 = Color(red: 41/255, green: 37/255, blue: 36/255)
        static let taupe800 = Color(red: 28/255, green: 25/255, blue: 23/255)
    }

    // MARK: - Trending Data
    private struct TrendingTag: Identifiable {
        let id = UUID()
        let titleKey: String
        let code: String
    }
    
    private let trendingTags: [TrendingTag] = [
        .init(titleKey: "funds.discover.suggestion.bosera_gold", code: "159937"),
        .init(titleKey: "funds.discover.suggestion.huaan_gold", code: "518880"),
        .init(titleKey: "funds.discover.suggestion.efund_info", code: "161128"),
        .init(titleKey: "funds.discover.suggestion.csi300", code: "510300"),
        .init(titleKey: "funds.discover.suggestion.nasdaq100", code: "513100")
    ]

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

    var body: some View {
        NavigationStack {
            ZStack {
                TaupeTheme.background.ignoresSafeArea()
                
                ScrollView {
                    VStack(alignment: .leading, spacing: 32) {
                        if searchText.isEmpty {
                            // 1. Trending Tags
                            VStack(alignment: .leading, spacing: 16) {
                                sectionHeader("funds.discover.trending_tags")
                                FlowLayout(spacing: 8) {
                                    ForEach(trendingTags) { tag in
                                        tagPill(LocalizedStringKey(tag.titleKey), code: tag.code)
                                    }
                                }
                            }
                            .padding(.horizontal, 16)

                            // 2. Suggested Reading
                            VStack(alignment: .leading, spacing: 16) {
                                HStack {
                                    sectionHeader("funds.discover.suggested_reading")
                                    Spacer()
                                    Button(LocalizedStringKey("funds.discover.view_all")) { }
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundStyle(TaupeTheme.primary)
                                }
                                
                                VStack(spacing: 24) {
                                    readingItem(
                                        category: "funds.discover.category.market_analysis",
                                        title: "funds.discover.reading.item1.title",
                                        time: "funds.discover.reading.item1.time",
                                        imageUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuA7f1ahwmbrfvbNU0wVtYYroTd2qSegbWhQvw2_UtnMfEHO_QwYTxYd-0MDByZ8rZxXntsxRUKYj5mqRKJOJKIWks6zP6eHJDo_TzV5ryk7vh_UihD2aHCzx7dHABtyc1ouTBJxtrcoamDW2Tdtew-9RjMKXZU28OgitohU9WMy-b4VNbpfNYbruUuCb8NwoQV6D5j8JdcgyoraWJnW45NFK4DO4xQuncEUKVjU8zqN7KfRLZC26ri3-VlML1tFcJQj3EVQBdqBb2U"
                                    )
                                    readingItem(
                                        category: "funds.discover.category.economy",
                                        title: "funds.discover.reading.item2.title",
                                        time: "funds.discover.reading.item2.time",
                                        imageUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuApDBYf5R8L4lzTgroIXOIlZIs_jWPaU_fCkvYN04_Ai0h5SwWcvmjWg1ZdznAZtPqRI0YsLFvVHDXquqJTMocU30ZfjFBybaJJgeHDh93_SGZ3ZwkBsoch8VX_vpouG9hrHnWwdNzNllarBYeKlZGUu45QHS_Rrsi3wd3aPq-Tpz_ZBR9G4P-NWemvLTU-GRGQ-YKIbhG1zdZCAtPNSHjX-ZRbIBPO9m3nRlXtdb9NaUbaeIhuIcTklVO_gnMiygZUTa2xVzq6LE4"
                                    )
                                    readingItem(
                                        category: "funds.discover.category.technical_insight",
                                        title: "funds.discover.reading.item3.title",
                                        time: "funds.discover.reading.item3.time",
                                        imageUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuAxmYcg8IkAtVHSexT_hDbs_PvovGWlT9VocU8JWWsERzHvAaK7pN2JjVzSA4HcSIqEValuegITwodDKovzTRXuirdHzDoKTE_X0Adz1O1SsHBJwrFiO8T3YXACNJYJqJGXp72x2Vq-mpDsyjkEZeQR2S8HBrXLnlgA1op1HNpqkqkpQWeUjGP1fe_v2Tci58yM5VaH1Z7GiskJqBZFialeMUuZzE00w0Hlls0w4YeQyN0FTuUaTImgkT2XQ1jC8PnLaRHmsLiSCWEg-7A"
                                    )
                                }
                            }
                            .padding(.horizontal, 16)

                            // 3. Recent Searches
                            if !recentSearches.isEmpty {
                                VStack(alignment: .leading, spacing: 16) {
                                    HStack {
                                        sectionHeader("funds.search.recent")
                                        Spacer()
                                        Button(LocalizedStringKey("common.action.clear")) { clearRecentSearches() }
                                            .font(.system(size: 10, weight: .bold))
                                            .kerning(-0.5)
                                            .foregroundStyle(TaupeTheme.taupe500)
                                    }
                                    VStack(spacing: 0) {
                                        ForEach(recentSearches) { item in
                                            historyRow(item: item)
                                        }
                                    }
                                }
                                .padding(.horizontal, 16)
                            }
                        } else {
                            // 4. Search Results
                            VStack(spacing: 16) {
                                if viewModel.isLoading {
                                    ProgressView().tint(TaupeTheme.primary).padding(.top, 20)
                                } else if filteredResults.isEmpty && !viewModel.results.isEmpty {
                                    Text("funds.search.filters.empty").foregroundStyle(TaupeTheme.taupe500).padding(.top, 20)
                                } else if viewModel.results.isEmpty && searchText.count >= 2 {
                                    emptyStateView.padding(.top, 40)
                                } else {
                                    VStack(spacing: 0) {
                                        ForEach(filteredResults) { fund in
                                            searchResultRow(fund: fund)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    .padding(.vertical, 24)
                }
                .background(TaupeTheme.background)
                .toolbar {
                    if !searchText.isEmpty {
                        ToolbarItem(placement: .topBarLeading) {
                            HStack(spacing: 12) {
                                ForEach(SearchFilterType.allCases, id: \.self) { filter in
                                    Button {
                                        withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                                            searchFilter = filter
                                        }
                                    } label: {
                                        Text(LocalizedStringKey(filter.rawValue))
                                            .foregroundStyle(searchFilter == filter ? TaupeTheme.primary : TaupeTheme.taupe400)
                                            .glassEffect(.regular, in: .rect(cornerRadius: 24))
                                    }
                                }
                            }
                        }
                    }
                }
                // Toast
                if showAddedToast {
                    VStack { Spacer(); toastView }.transition(.move(edge: .bottom).combined(with: .opacity)).zIndex(100)
                }
            }
            .navigationDestination(item: $selectedFundToView) { valuation in
                FundDetailView(valuation: valuation)
            }
            .confirmationDialog(LocalizedStringKey("funds.group.select_title"), isPresented: $showGroupSelection, titleVisibility: .visible) {
                Button("funds.group.default") { if let fund = pendingFundToAdd { Task { await performAdd(fund: fund, groupId: nil) } } }
                ForEach(watchlistViewModel.groups) { group in
                    Button(group.name) { if let fund = pendingFundToAdd { Task { await performAdd(fund: fund, groupId: group.id) } } }
                }
                Button("funds.action.cancel", role: .cancel) { pendingFundToAdd = nil }
            }
            .onChange(of: searchText) {
                viewModel.query = searchText
                Task { await viewModel.performSearch() }
            }
            .onAppear {
                loadRecentSearches()
                Task { await watchlistViewModel.fetchGroups() }
            }
        }
    }

    // MARK: - Subcomponents
    private func sectionHeader(_ title: LocalizedStringKey) -> some View {
        Text(title)
            .textCase(.uppercase)
            .font(.system(size: 11, weight: .bold))
            .kerning(1.5)
            .foregroundStyle(TaupeTheme.taupe400)
    }

    private func tagPill(_ title: LocalizedStringKey, code: String) -> some View {
        Button { searchText = code } label: {
            Text(title).font(.system(size: 13, weight: .medium)).foregroundStyle(TaupeTheme.taupe100)
                .padding(.horizontal, 16).padding(.vertical, 8).background(TaupeTheme.taupe700).clipShape(Capsule())
        }.buttonStyle(.plain)
    }

    private func readingItem(category: LocalizedStringKey, title: LocalizedStringKey, time: LocalizedStringKey, imageUrl: String) -> some View {
        HStack(spacing: 16) {
            AsyncImage(url: URL(string: imageUrl)) { image in
                image.resizable()
                    .aspectRatio(contentMode: .fill)
            } placeholder: {
                Rectangle().fill(TaupeTheme.taupe800)
            }
            .frame(width: 80, height: 80)
            .clipShape(RoundedRectangle(cornerRadius: 4))
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(TaupeTheme.taupe700, lineWidth: 0.5))
            
            VStack(alignment: .leading, spacing: 4) {
                Text(category)
                    .textCase(.uppercase)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(TaupeTheme.primary)
                Text(title)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(TaupeTheme.taupe100)
                    .lineLimit(2)
                    .lineSpacing(2)
                Text(time)
                    .font(.system(size: 12))
                    .foregroundStyle(TaupeTheme.taupe400)
            }
        }
    }

    private func historyRow(item: FundSearchHistoryItem) -> some View {
        Button { searchText = item.code } label: {
            HStack(spacing: 12) {
                Image(systemName: "clock")
                    .font(.system(size: 14))
                    .foregroundStyle(TaupeTheme.taupe500)
                Text(item.name)
                    .font(.system(size: 14))
                    .foregroundStyle(TaupeTheme.taupe300)
                Spacer()
                Button {
                    removeRecentSearch(code: item.code)
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12))
                        .foregroundStyle(TaupeTheme.taupe600)
                }
            }
            .padding(.vertical, 14)
            .border(width: 1, edges: [.bottom], color: TaupeTheme.taupe800.opacity(0.5))
        }.buttonStyle(.plain)
    }

    private func searchResultRow(fund: FundSearchResult) -> some View {
        let isAdded = addedFunds.contains(fund.code)
        return HStack(spacing: 12) {
            Button {
                let dummyValuation = FundValuation(fundCode: fund.code, fundName: fund.name, estimatedGrowth: 0, totalWeight: 0, components: [], timestamp: Date(), stats: nil)
                selectedFundToView = dummyValuation
                saveRecentSearch(code: fund.code, name: fund.name)
            } label: {
                VStack(alignment: .leading, spacing: 4) {
                    Text(fund.name).font(.system(size: 15, weight: .medium)).foregroundStyle(isAdded ? .secondary : TaupeTheme.taupe100).lineLimit(1)
                    HStack(spacing: 6) {
                        Text(fund.code).font(.system(size: 10, design: .monospaced)).foregroundStyle(TaupeTheme.taupe400)
                            .padding(.horizontal, 4).padding(.vertical, 2).background(TaupeTheme.taupe800).clipShape(RoundedRectangle(cornerRadius: 2))
                        if let type = fund.type, !type.isEmpty {
                            Text(type).font(.system(size: 9, weight: .bold)).foregroundStyle(TaupeTheme.primary)
                        }
                    }
                }
            }.buttonStyle(.plain)
            Spacer()
            if let valuation = viewModel.valuations[fund.code] {
                Text(String(format: "%+.2f%%", valuation.estimatedGrowth)).font(.system(size: 14, weight: .bold, design: .monospaced))
                    .foregroundStyle(valuation.estimatedGrowth > 0 ? Color.Alpha.down : (valuation.estimatedGrowth < 0 ? Color.Alpha.up : Color.Alpha.neutral))
            }
            LiquidAddButton(isAdded: isAdded) {
                if !isAdded { pendingFundToAdd = fund; showGroupSelection = true } else { await performRemove(fund: fund) }
            }
        }.padding(.vertical, 12).padding(.horizontal, 16).border(width: 0.5, edges: [.bottom], color: TaupeTheme.taupe800)
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.text.magnifyingglass").font(.system(size: 40)).foregroundStyle(TaupeTheme.taupe700)
            Text("funds.search.not_found").font(.subheadline).foregroundStyle(TaupeTheme.taupe500)
        }.frame(maxWidth: .infinity).padding(.vertical, 60)
    }

    private var toastView: some View {
        HStack(spacing: 8) {
            Image(systemName: toastType.icon).foregroundStyle(toastType.color)
            Text(toastMessage).foregroundStyle(TaupeTheme.taupe100)
        }.font(.system(size: 13, weight: .medium)).padding(.vertical, 12).padding(.horizontal, 20).background(TaupeTheme.taupe800).clipShape(Capsule()).padding(.bottom, 20).shadow(color: .black.opacity(0.3), radius: 10)
    }

    // MARK: - Logic (Preserved)
    private func performAdd(fund: FundSearchResult, groupId: String?) async {
        addedFunds.insert(fund.code); toastMessage = String(format: String(localized: "app.funds.added_%@"), arguments: [fund.name]); toastType = .success
        withAnimation(.spring()) { showAddedToast = true }; saveRecentSearch(code: fund.code, name: fund.name)
        await watchlistViewModel.addFund(code: fund.code, name: fund.name, groupId: groupId)
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { withAnimation(.easeInOut) { showAddedToast = false } }
    }
    private func performRemove(fund: FundSearchResult) async {
        addedFunds.remove(fund.code); toastMessage = String(format: String(localized: "app.funds.removed_%@"), arguments: [fund.name]); toastType = .info
        withAnimation(.spring()) { showAddedToast = true }; await watchlistViewModel.deleteFund(code: fund.code)
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { withAnimation(.easeInOut) { showAddedToast = false } }
    }
    private func loadRecentSearches() { if let decoded = try? JSONDecoder().decode([FundSearchHistoryItem].self, from: recentSearchesData) { recentSearches = decoded } }
    private func saveRecentSearch(code: String, name: String) {
        let newItem = FundSearchHistoryItem(code: code, name: name); var current = recentSearches; current.removeAll { $0.code == code }
        current.insert(newItem, at: 0); if current.count > 10 { current = Array(current.prefix(10)) }
        withAnimation { recentSearches = current }; if let encoded = try? JSONEncoder().encode(current) { recentSearchesData = encoded }
    }
    private func removeRecentSearch(code: String) {
        var current = recentSearches
        current.removeAll { $0.code == code }
        withAnimation { recentSearches = current }
        if let encoded = try? JSONEncoder().encode(current) { recentSearchesData = encoded }
    }
    private func clearRecentSearches() { withAnimation { recentSearches.removeAll() }; recentSearchesData = Data() }
}
// MARK: - Helper Views & Models (Preserved)
struct FlowLayout: Layout {
    var spacing: CGFloat
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.replacingUnspecifiedDimensions().width; var currentX: CGFloat = 0; var currentY: CGFloat = 0; var lineHeight: CGFloat = 0; var totalHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified); if currentX + size.width > width { currentX = 0; currentY += lineHeight + spacing; lineHeight = 0 }
            currentX += size.width + spacing; lineHeight = max(lineHeight, size.height); totalHeight = currentY + lineHeight
        }
        return CGSize(width: width, height: totalHeight)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var currentX: CGFloat = bounds.minX; var currentY: CGFloat = bounds.minY; var lineHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified); if currentX + size.width > bounds.maxX { currentX = bounds.minX; currentY += lineHeight + spacing; lineHeight = 0 }
            subview.place(at: CGPoint(x: currentX, y: currentY), proposal: .unspecified); currentX += size.width + spacing; lineHeight = max(lineHeight, size.height)
        }
    }
}
extension View { func border(width: CGFloat, edges: [Edge], color: Color) -> some View { overlay(EdgeBorder(width: width, edges: edges).foregroundColor(color)) } }
struct EdgeBorder: Shape {
    var width: CGFloat; var edges: [Edge]
    func path(in rect: CGRect) -> Path {
        var path = Path(); for edge in edges {
            var x: CGFloat { switch edge { case .top, .bottom, .leading: return rect.minX; case .trailing: return rect.maxX - width } }
            var y: CGFloat { switch edge { case .top, .leading, .trailing: return rect.minY; case .bottom: return rect.maxY - width } }
            var w: CGFloat { switch edge { case .top, .bottom: return rect.width; case .leading, .trailing: return width } }
            var h: CGFloat { switch edge { case .top, .bottom: return width; case .leading, .trailing: return rect.height } }
            path.addRect(CGRect(x: x, y: y, width: w, height: h))
        }
        return path
    }
}
enum SearchFilterType: String, CaseIterable { case all = "funds.search.filter.all", stocks = "funds.search.filter.stocks", funds = "funds.search.filter.funds" }
struct FundSearchHistoryItem: Codable, Identifiable, Equatable { var id: String { code }; let code: String; let name: String }
