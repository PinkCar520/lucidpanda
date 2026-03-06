import SwiftUI
import AlphaDesign
import AlphaData
import SwiftData
import AlphaCore
import Combine

struct MainDashboardView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel = DashboardViewModel()
    @Environment(AppRootViewModel.self) private var rootViewModel
    @State private var isSettingsPresented = false
    @State private var marketQuotes: [String: MarketQuote] = [:]
    @State private var isFetchingMarketData = false

    @State private var currentTime = Date()
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    @Query(sort: \IntelligenceModel.timestamp, order: .reverse)
    private var cachedItems: [IntelligenceModel]

    var body: some View {
        @Bindable var viewModel = viewModel
        return NavigationStack {
            ZStack {
                LiquidBackground()

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 0) {
                        // 1. 顶部状态栏
                        headerSection
                            .padding(.bottom, 16)

                        // 2. 四品种市场数据 (黄金、美元指数、原油、美债十年期)
                        marketDataSection
                            .padding(.bottom, 16)

                        // 3. 搜索与过滤器 (对齐 Web 端)
                        searchAndFilterBar

                        VStack(spacing: 16) {
                            let displayItems = viewModel.items.isEmpty ? cachedItems.map { IntelligenceItem(from: $0) } : viewModel.filteredItems

                            if displayItems.isEmpty {
                                emptyStateView
                            } else {
                                LazyVStack(spacing: viewModel.filterMode == .bullish || viewModel.filterMode == .bearish ? 0 : 16) {
                                    if viewModel.filterMode == .bullish || viewModel.filterMode == .bearish {
                                        correlationHeader(mode: viewModel.filterMode)
                                    }
                                    
                                    ForEach(Array(displayItems.enumerated()), id: \.element.id) { index, item in
                                        Group {
                                            if viewModel.filterMode == .bullish || viewModel.filterMode == .bearish {
                                                timelineItem(item: item, isLast: index == displayItems.count - 1)
                                            } else {
                                                NavigationLink(destination: IntelligenceDetailView(item: item)) {
                                                    IntelligenceItemCard(item: item)
                                                }
                                                .buttonStyle(LiquidScaleButtonStyle())
                                            }
                                        }
                                        .scrollTransition(
                                            topLeading: .interactive,
                                            bottomTrailing: .interactive
                                        ) { content, phase in
                                            content
                                                .opacity(phase.isIdentity ? 1 : (phase.value < 0 ? 0.3 : 1))
                                                .scaleEffect(phase.isIdentity ? 1 : (phase.value < 0 ? 0.85 : 1))
                                                .offset(y: phase.value < 0 ? (phase.value * 50) : 0)
                                                .blur(radius: phase.value < 0 ? (abs(phase.value) * 5) : 0)
                                        }
                                    }
                                }
                                .padding(.horizontal)
                            }

                            Spacer(minLength: 100)
                        }
                        .padding(.top, 16)
                    }
                }
                
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        isSettingsPresented = true
                    } label: {
                        let displayEmail = rootViewModel.userProfile?.email ?? "root@alphasignal.com"
                        let initial = String(displayEmail.prefix(1)).uppercased()
                        
                        Group {
                            if let avatarUrl = rootViewModel.userProfile?.avatarUrl {
                                let absoluteUrl = URL(string: avatarUrl, relativeTo: APIClient.shared.baseURL)
                                AsyncImage(url: absoluteUrl) { image in
                                    image
                                        .resizable()
                                        .scaledToFill()
                                        .clipShape(Circle())
                                } placeholder: {
                                    Circle().fill(Color(uiColor: .secondarySystemFill))
                                }
                                .frame(width: 30, height: 30)
                            } else {
                                Text(initial)
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(.primary)
                                    .frame(width: 30, height: 30)
                                    .clipShape(Circle())
                            }
                        }
                        .glassEffect(.clear.interactive())
                        .frame(width: 30, height: 30)
                    }
                    .accessibilityLabel(Text("dashboard.action.open_settings"))
                }
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            viewModel.setModelContext(modelContext)
        }
        .task {
            await viewModel.startIntelligenceStream()
            await fetchMarketData()
        }
        .onDisappear {
            viewModel.stopIntelligenceStream()
        }
        .sheet(isPresented: $isSettingsPresented) {
            SettingsView(showCloseButton: true)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
    }
    
    private var headerSection: some View {
        let activeAlertsCount = viewModel.filteredItems.filter { $0.urgencyScore >= 8 }.count

        return VStack(alignment: .leading, spacing: 16) {
            Text("dashboard.title")
                .font(.title2.weight(.bold))
                .foregroundStyle(.primary)

            HStack(spacing: 12) {
                // 1. 活跃警报 (Active Alerts)
                VStack(spacing: 2) {
                    Text("dashboard.active_alerts")
                        .font(.system(size: 10, weight: .bold))
                        .textCase(.uppercase)
                        .foregroundStyle(.secondary)

                    Text("\(activeAlertsCount)")
                        .font(.system(size: 22, weight: .black, design: .monospaced))
                        .foregroundStyle(activeAlertsCount > 0 ? .red : .primary)
                }
                .frame(width: 80, height: 64)
                .background(Color(uiColor: .systemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .shadow(color: .black.opacity(0.04), radius: 6, x: 0, y: 2)

                // 2. 实时状态 & UTC (Real-time Status & UTC Time)
                VStack(alignment: .leading, spacing: 0) {
                    HStack {
                        Circle()
                            .fill(statusColor)
                            .frame(width: 8, height: 8)

                        Text(LocalizedStringKey(statusText))
                            .font(.system(size: 12, weight: .bold, design: .monospaced))
                            .foregroundStyle(statusColor)
                        Spacer()
                    }
                    .padding(.horizontal, 12)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(statusColor.opacity(0.1))

                    Divider().opacity(0.5)

                    HStack {
                        Image(systemName: "globe")
                            .font(.system(size: 10))
                        Text("UTC \(utcDateFormatter.string(from: currentTime))")
                            .font(.system(size: 11, weight: .medium, design: .monospaced))
                        Spacer()
                    }
                    .padding(.horizontal, 12)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(uiColor: .systemBackground))
                }
                .frame(height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .shadow(color: .black.opacity(0.04), radius: 6, x: 0, y: 2)
            }
        }
        .padding(.horizontal)
        .padding(.top, 24)
        .onReceive(timer) { input in
            currentTime = input
            
            // 每 30 秒自动刷新一次市场数据卡片
            let seconds = Calendar.current.component(.second, from: input)
            if seconds % 30 == 0 {
                Task {
                    await fetchMarketData()
                }
            }
        }
    }

    /// 四品种市场数据区域
    private var marketDataSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("dashboard.market.title")
                    .font(.system(size: 16, weight: .bold))
                Spacer()
                NavigationLink(destination: MarketTerminalView()) {
                    Text("terminal.view_all")
                        .font(.system(size: 12))
                        .foregroundStyle(.blue)
                }
            }
            .padding(.horizontal)

            LazyVGrid(
                columns: [GridItem(.flexible()), GridItem(.flexible())],
                spacing: 10
            ) {
                MarketQuoteRow(
                    symbol: "黄金",
                    quote: marketQuotes["gold"]
                )
                MarketQuoteRow(
                    symbol: "美元指数",
                    quote: marketQuotes["dxy"]
                )
                MarketQuoteRow(
                    symbol: "原油",
                    quote: marketQuotes["oil"]
                )
                MarketQuoteRow(
                    symbol: "美债 10Y",
                    quote: marketQuotes["us10y"]
                )
            }
            .padding(.horizontal)
        }
        .task {
            await fetchMarketData()
        }
    }
    
    private var utcDateFormatter: DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        formatter.timeZone = TimeZone(abbreviation: "UTC")
        return formatter
    }

    // 系统状态文本（3 种状态）
    private var statusText: String {
        switch viewModel.connectionStatus {
        case "dashboard.connection.live":
            return "dashboard.system.operational"
        case "dashboard.connection.connecting":
            return "dashboard.connection.connecting"
        default:
            return "dashboard.system.degraded"
        }
    }

    // 系统状态颜色
    private var statusColor: Color {
        switch viewModel.connectionStatus {
        case "dashboard.connection.live":
            return .green
        case "dashboard.connection.connecting":
            return .orange
        default:
            return .red
        }
    }

    private var searchAndFilterBar: some View {
        VStack(spacing: 12) {
            // 过滤器切换 - 支持横向滚动
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    filterButton(titleKey: "dashboard.filter.all", mode: .all)
                    filterButton(titleKey: "dashboard.filter.score8", mode: .essential)
                    filterButton(titleKey: "dashboard.filter.bearish", mode: .bearish)
                    filterButton(titleKey: "dashboard.filter.bullish", mode: .bullish)
                }
                .padding(.horizontal)
            }
            .frame(height: 50) // 确保有足够的高度显示按钮
        }
    }
    
    private func filterButton(titleKey: String, mode: DashboardViewModel.FilterMode) -> some View {
        Button {
            withAnimation(.spring(response: 0.3)) {
                viewModel.filterMode = mode
            }
        } label: {
            Text(LocalizedStringKey(titleKey))
                .font(.system(size: 14, weight: .bold))
                .padding(.horizontal, 28)
                .padding(.vertical, 14)
                .foregroundStyle(viewModel.filterMode == mode ? Color.blue : Color.primary)
                .glassEffect(.regular, in: .capsule)
                .clipShape(Capsule())
        }
    }

    
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Spacer(minLength: 100)
            if viewModel.items.isEmpty && viewModel.isStreaming {
                ProgressView().tint(.primary)
                Text("dashboard.loading_feed")
            } else {
                Image(systemName: "tray.and.arrow.down")
                    .font(.system(size: 40))
                    .foregroundStyle(.gray.opacity(0.2))
                Text("dashboard.empty.no_match")
            }
        }
        .font(.system(size: 12, weight: .bold, design: .monospaced))
        .foregroundStyle(.gray.opacity(0.5))
    }

    private func t(_ key: String) -> String {
        NSLocalizedString(key, comment: "")
    }
    
    // MARK: - Timeline Views
    
    @ViewBuilder
    private func correlationHeader(mode: DashboardViewModel.FilterMode) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: "point.3.connected.trianglepath.dotted")
                Text(LocalizedStringKey(mode == .bullish ? "dashboard.correlation.bullish_title" : "dashboard.correlation.bearish_title"))
            }
            .font(.headline)
            .foregroundStyle(mode == .bullish ? .green : .red)
            
            Text(LocalizedStringKey(mode == .bullish ? "dashboard.correlation.bullish_desc" : "dashboard.correlation.bearish_desc"))
                .font(.caption)
                .foregroundStyle(.secondary)
            
            Divider().padding(.vertical, 8)
        }
        .padding(.bottom, 8)
    }
    
    @ViewBuilder
    private func timelineItem(item: IntelligenceItem, isLast: Bool) -> some View {
        HStack(alignment: .top, spacing: 12) {

            // Timeline line & dot
            VStack(spacing: 0) {
                Circle()
                    .fill(item.urgencyScore >= 8 ? .red : .blue)
                    .frame(width: 10, height: 10)
                    .overlay(
                        Circle().stroke(Color(uiColor: .systemBackground), lineWidth: 2)
                    )
                    .shadow(color: (item.urgencyScore >= 8 ? Color.red : Color.blue).opacity(0.3), radius: 4)

                if !isLast {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(width: 2)
                        .padding(.vertical, 4)
                }
            }
            .padding(.top, 15)

            // Card Content
            VStack {
                NavigationLink(destination: IntelligenceDetailView(item: item)) {
                    IntelligenceItemCard(item: item)
                }
                .buttonStyle(LiquidScaleButtonStyle())
            }
            .padding(.bottom, isLast ? 0 : 20)
        }
    }

    // MARK: - Market Data Methods

    private func fetchMarketData() async {
        guard !isFetchingMarketData else { return }
        await MainActor.run {
            isFetchingMarketData = true
        }

        do {
            let snapshot: MarketSnapshot = try await APIClient.shared.fetch(path: "/api/v1/mobile/market/snapshot")
            await MainActor.run {
                marketQuotes["gold"] = snapshot.gold
                marketQuotes["dxy"] = snapshot.dxy
                marketQuotes["oil"] = snapshot.oil
                marketQuotes["us10y"] = snapshot.us10y
                isFetchingMarketData = false
            }
        } catch {
            print("Failed to fetch market data: \(error)")
            await MainActor.run {
                isFetchingMarketData = false
            }
        }
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        return formatter.string(from: date)
    }
}

// MARK: - Market Quote Row

/// 市场报价行组件
struct MarketQuoteRow: View {
    let symbol: String
    let quote: MarketQuote?

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(symbol)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(.secondary)

                if let quote = quote, quote.price > 0 {
                    Text(formatPrice(quote.price, symbol: symbol))
                        .font(.system(size: 14, weight: .bold, design: .monospaced))
                        .foregroundStyle(.primary)
                } else {
                    Text("--")
                        .font(.system(size: 14, weight: .bold, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()

            if let quote = quote, quote.price > 0 {
                VStack(alignment: .trailing, spacing: 2) {
                    let isPositive = quote.change >= 0
                    let trendColor = isPositive ? Color.red : Color.green
                    let icon = isPositive ? "arrow.up.right" : "arrow.down.right"

                    HStack(spacing: 2) {
                        Image(systemName: icon)
                            .font(.system(size: 9, weight: .bold))
                        Text(formatChange(quote.change))
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                    }
                    .foregroundStyle(trendColor)

                    Text(formatChangePercent(quote.changePercent))
                        .font(.system(size: 10, weight: .medium, design: .monospaced))
                        .foregroundStyle(trendColor)
                }
            } else {
                Text("--")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.secondary)
            }
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(.systemBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(Color.gray.opacity(0.1), lineWidth: 1)
        )
    }

    private func formatPrice(_ price: Double, symbol: String) -> String {
        // 美债 10Y 和美元指数保留 2 位小数，黄金和原油保留 1 位小数
        if symbol == "美债 10Y" || symbol == "美元指数" {
            return String(format: "%.2f", price)
        } else {
            return String(format: "%.1f", price)
        }
    }

    private func formatChange(_ change: Double) -> String {
        return String(format: "%+.2f", change)
    }

    private func formatChangePercent(_ percent: Double) -> String {
        return String(format: "%+.2f%%", percent)
    }
}

// 增加转换构造函数
extension IntelligenceItem {
    init(from model: IntelligenceModel) {
        self.init(
            id: model.id,
            timestamp: model.timestamp,
            author: model.author,
            summary: model.summary,
            content: model.content,
            sentiment: model.sentiment,
            urgencyScore: model.urgencyScore,
            goldPriceSnapshot: model.goldPriceSnapshot
        )
    }
}
