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
    
    // Discovery Navigation & Loading
    @State private var selectedIntelligence: IntelligenceItem?
    @State private var loadingReadingId: Int?
    
    // Group Selection
    @State private var showGroupSelection = false
    @State private var pendingFundToAdd: FundSearchResult?
    @Environment(\.colorScheme) var colorScheme

    @AppStorage("recent_fund_searches") private var recentSearchesData: Data = Data()
    @State private var recentSearches: [FundSearchHistoryItem] = []

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
                Color.Alpha.background.ignoresSafeArea()
                
                ScrollView {
                    VStack(alignment: .leading, spacing: 32) {
                        if searchText.isEmpty {
                            // 1. Trending Tags
                            VStack(alignment: .leading, spacing: 16) {
                                sectionHeader("funds.discover.trending_tags")
                                
                                if viewModel.isDiscoveryLoading && viewModel.trendingTags.isEmpty {
                                    HStack {
                                        ProgressView().scaleEffect(0.8)
                                        Text("common.loading").font(.caption).foregroundStyle(.secondary)
                                    }
                                } else {
                                    FlowLayout(spacing: 8) {
                                        ForEach(viewModel.trendingTags) { tag in
                                            tagPill(tag.title, code: tag.code)
                                        }
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
                                        .font(.system(size: 11, weight: .black))
                                        .foregroundStyle(Color.Alpha.brand)
                                }
                                
                                if viewModel.isDiscoveryLoading && viewModel.suggestedReading.isEmpty {
                                    ProgressView().padding(.vertical, 20)
                                } else {
                                    VStack(spacing: 24) {
                                        ForEach(viewModel.suggestedReading) { item in
                                            Button {
                                                Task { await navigateToReading(item) }
                                            } label: {
                                                ZStack(alignment: .trailing) {
                                                    readingItem(
                                                        category: LocalizedStringKey(item.categoryKey),
                                                        title: item.title,
                                                        time: item.timestamp.formatted(date: .omitted, time: .shortened),
                                                        imageUrl: item.imageUrl
                                                    )
                                                    
                                                    if loadingReadingId == item.id {
                                                        ProgressView()
                                                            .tint(Color.Alpha.brand)
                                                            .padding(.trailing, 8)
                                                    }
                                                }
                                            }
                                            .buttonStyle(LiquidScaleButtonStyle())
                                            .disabled(loadingReadingId != nil)
                                        }
                                    }
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
                                            .foregroundStyle(Color.Alpha.textSecondary.opacity(0.6))
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
                                    ProgressView().tint(Color.Alpha.brand).padding(.top, 20)
                                } else if filteredResults.isEmpty && !viewModel.results.isEmpty {
                                    Text("funds.search.filters.empty").foregroundStyle(Color.Alpha.textSecondary).padding(.top, 20)
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
                .background(Color.Alpha.background)
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
                                            .font(.system(size: 12, weight: .bold))
                                            .foregroundStyle(searchFilter == filter ? (colorScheme == .dark ? .white : Color.Alpha.brand) : Color.Alpha.textSecondary)
                                            .padding(.horizontal, 12)
                                            .padding(.vertical, 6)
                                            .background(
                                                Capsule()
                                                    .fill(searchFilter == filter ? Color.Alpha.brand.opacity(0.1) : Color.clear)
                                            )
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
            .navigationDestination(item: $selectedIntelligence) { item in
                IntelligenceDetailView(item: item)
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
            .task {
                loadRecentSearches()
                await viewModel.fetchDiscovery()
                await watchlistViewModel.fetchGroups()
            }
        }
    }

    // MARK: - Subcomponents
    private func sectionHeader(_ title: LocalizedStringKey) -> some View {
        Text(title)
            .textCase(.uppercase)
            .font(.system(size: 11, weight: .black))
            .kerning(1.5)
            .foregroundStyle(Color.Alpha.textSecondary.opacity(0.7))
    }

    private func tagPill(_ title: String, code: String) -> some View {
        Button { searchText = code } label: {
            Text(title).font(.system(size: 13, weight: .bold)).foregroundStyle(Color.Alpha.textPrimary)
                .padding(.horizontal, 16).padding(.vertical, 10).background(colorScheme == .dark ? Color.Alpha.surface : Color.Alpha.surfaceContainerLow).clipShape(Capsule())
        }.buttonStyle(.plain)
    }

    private func readingItem(category: LocalizedStringKey, title: String, time: String, imageUrl: String) -> some View {
        HStack(spacing: 16) {
            let encodedUrl = imageUrl.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
            let proxyUrl = URL(string: "/api/v1/mobile/image?url=\(encodedUrl)", relativeTo: APIClient.shared.baseURL)
            
            AsyncImage(url: proxyUrl) { image in
                image.resizable()
                    .aspectRatio(contentMode: .fill)
            } placeholder: {
                Rectangle().fill(Color.Alpha.surfaceContainerLow)
            }
            .frame(width: 90, height: 90)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.Alpha.separator, lineWidth: 0.5))
            
            VStack(alignment: .leading, spacing: 6) {
                Text(category)
                    .textCase(.uppercase)
                    .font(.system(size: 10, weight: .black))
                    .foregroundStyle(Color.Alpha.brand)
                Text(title)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .lineLimit(2)
                    .lineSpacing(2)
                Text(time)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.6))
            }
        }
    }

    private func historyRow(item: FundSearchHistoryItem) -> some View {
        Button { searchText = item.code } label: {
            HStack(spacing: 12) {
                Image(systemName: "clock.fill")
                    .font(.system(size: 12))
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.4))
                Text(item.name)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(Color.Alpha.textPrimary)
                Spacer()
                Button {
                    removeRecentSearch(code: item.code)
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color.Alpha.textSecondary.opacity(0.3))
                }
            }
            .padding(.vertical, 14)
            .border(width: 0.5, edges: [.bottom], color: Color.Alpha.separator)
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
                    Text(fund.name).font(.system(size: 16, weight: .bold)).foregroundStyle(isAdded ? Color.Alpha.textSecondary : Color.Alpha.textPrimary).lineLimit(1)
                    HStack(spacing: 6) {
                        Text(fund.code).font(.system(size: 11, weight: .bold, design: .monospaced)).foregroundStyle(Color.Alpha.textSecondary.opacity(0.7))
                            .padding(.horizontal, 6).padding(.vertical, 2).background(Color.Alpha.surfaceContainerLow).clipShape(RoundedRectangle(cornerRadius: 4))
                        if let type = fund.type, !type.isEmpty {
                            Text(type).font(.system(size: 9, weight: .black)).foregroundStyle(Color.Alpha.brand)
                        }
                    }
                }
            }.buttonStyle(.plain)
            Spacer()
            if let valuation = viewModel.valuations[fund.code] {
                Text(String(format: "%+.2f%%", valuation.estimatedGrowth)).font(.system(size: 15, weight: .black, design: .monospaced))
                    .foregroundStyle(valuation.estimatedGrowth > 0 ? Color.Alpha.down : (valuation.estimatedGrowth < 0 ? Color.Alpha.up : Color.Alpha.neutral))
            }
            LiquidAddButton(isAdded: isAdded) {
                if !isAdded { pendingFundToAdd = fund; showGroupSelection = true } else { await performRemove(fund: fund) }
            }
        }.padding(.vertical, 14).padding(.horizontal, 16).border(width: 0.5, edges: [.bottom], color: Color.Alpha.separator)
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "magnifyingglass.circle.fill").font(.system(size: 48)).foregroundStyle(Color.Alpha.textSecondary.opacity(0.2))
            Text("funds.search.not_found").font(.system(size: 14, weight: .bold)).foregroundStyle(Color.Alpha.textSecondary.opacity(0.5))
        }.frame(maxWidth: .infinity).padding(.vertical, 80)
    }

    private var toastView: some View {
        HStack(spacing: 10) {
            Image(systemName: toastType.icon).foregroundStyle(toastType.color).font(.system(size: 16, weight: .bold))
            Text(toastMessage).foregroundStyle(Color.Alpha.textPrimary).font(.system(size: 14, weight: .bold))
        }.padding(.vertical, 14).padding(.horizontal, 24).background(Color.Alpha.surfaceContainerLowest).clipShape(Capsule()).padding(.bottom, 30).shadow(color: Color.black.opacity(0.12), radius: 20, x: 0, y: 10)
    }

    // MARK: - Logic (Preserved)
    private func navigateToReading(_ reading: SuggestedReadingDTO) async {
        let generator = UIImpactFeedbackGenerator(style: .medium)
        generator.impactOccurred()
        
        loadingReadingId = reading.id
        defer { loadingReadingId = nil }
        
        do {
            let detail = try await viewModel.fetchIntelligenceDetail(id: reading.id)
            selectedIntelligence = detail
        } catch {
            print("Failed to fetch reading detail: \(error)")
        }
    }

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
