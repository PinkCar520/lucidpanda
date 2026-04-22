import SwiftUI
import AlphaDesign
import AlphaData
import SwiftData
import AlphaCore
import Combine

struct MainDashboardView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.colorScheme) private var colorScheme
    @State private var viewModel = DashboardViewModel()
    @Environment(AppRootViewModel.self) private var rootViewModel
    @State private var isSettingsPresented = false
    @State private var isPulseSheetPresented = false

    @State private var currentTime = Date()
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    @Query(sort: \IntelligenceModel.timestamp, order: .reverse)
    private var cachedItems: [IntelligenceModel]

    var body: some View {
        @Bindable var viewModel = viewModel
        return NavigationStack {
            ZStack(alignment: .top) {
                Color.Alpha.background.ignoresSafeArea()

                VStack(spacing: 0) {
                    // 1. Sticky Real-time Ticker
                    goldTickerHeader
                    
                    ScrollView(showsIndicators: false) {
                        VStack(spacing: 0) {
                            let displayItems = viewModel.items.isEmpty ? cachedItems.map { IntelligenceItem(from: $0) } : viewModel.filteredItems

                            if displayItems.isEmpty {
                                emptyStateView.padding(.top, 100)
                            } else {
                                // 2. Featured Analysis (Top item)
                                if let featured = displayItems.first {
                                    NavigationLink(destination: IntelligenceDetailView(item: featured)) {
                                        IntelligenceItemCard(item: featured, style: .featured)
                                    }
                                    .buttonStyle(.plain)
                                    .padding(.horizontal)
                                    .padding(.vertical, 20)
                                }

                                // 3. News Section
                                VStack(alignment: .leading, spacing: 20) {
                                    sectionHeaderView

                                    LazyVStack(spacing: 12) {
                                        ForEach(Array(displayItems.dropFirst().enumerated()), id: \.element.id) { index, item in
                                            NavigationLink(destination: IntelligenceDetailView(item: item)) {
                                                IntelligenceItemCard(item: item, style: .standard)
                                            }
                                            .buttonStyle(LiquidScaleButtonStyle())
                                        }
                                    }
                                    .padding(.horizontal)
                                }
                                .padding(.top, 8)
                            }

                            Spacer(minLength: 120)
                        }
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        isSettingsPresented = true
                    } label: {
                        let displayEmail = rootViewModel.userProfile?.email ?? "root@lucidpanda.com"
                        let initial = String(displayEmail.prefix(1)).uppercased()
                        
                        Text(initial)
                            .font(.system(size: 10, weight: .black))
                            .foregroundStyle(Color.Alpha.brand)
                            .frame(width: 28, height: 28)
                            .background(Color.Alpha.brand.opacity(0.15))
                            .clipShape(Circle())
                            .overlay(Circle().stroke(Color.Alpha.brand.opacity(0.3), lineWidth: 1))
                    }
                }
            }
        }
        .onAppear {
            viewModel.setModelContext(modelContext)
        }
        .task {
            await viewModel.startIntelligenceStream()
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
    
    private var goldTickerHeader: some View {
        HStack {
            HStack(spacing: 8) {
                Circle()
                    .fill(Color.Alpha.brand)
                    .frame(width: 6, height: 6)
                    .opacity(isTickerAnimating ? 1 : 0.3)
                    .animation(.easeInOut(duration: 0.8).repeatForever(), value: isTickerAnimating)
                
                Text("dashboard.ticker.gold_label")
                    .font(.system(size: 10, weight: .black))
                    .textCase(.uppercase)
                    .kerning(1.2)
                    .foregroundStyle(Color.Alpha.brand)
            }
            
            Spacer()
            
            if let pulse = rootViewModel.marketPulseViewModel.pulseData {
                HStack(spacing: 12) {
                    Text(String(format: "$%.2f", pulse.marketSnapshot.gold.price))
                        .font(.system(size: 18, weight: .semibold, design: .monospaced))
                        .foregroundStyle(Color.Alpha.textPrimary)
                    
                    Text(String(format: "%+.2f%%", pulse.marketSnapshot.gold.changePercent))
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(pulse.marketSnapshot.gold.changePercent >= 0 ? Color.Alpha.up.opacity(0.15) : Color.Alpha.down.opacity(0.15))
                        .foregroundStyle(pulse.marketSnapshot.gold.changePercent >= 0 ? Color.Alpha.up : Color.Alpha.down)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .background(Color.Alpha.surface.opacity(0.85))
        .background(.ultraThinMaterial)
        .overlay(Divider().background(Color.Alpha.separator), alignment: .bottom)
        .onAppear { isTickerAnimating = true }
    }

    @State private var isTickerAnimating = false

    private var searchAndFilterBar: some View {
        Menu {
            Button { viewModel.filterMode = .all } label: { Label("dashboard.filter.all", systemImage: "line.3.horizontal") }
            Button { viewModel.filterMode = .essential } label: { Label("dashboard.filter.score8", systemImage: "bolt.fill") }
            Button { viewModel.filterMode = .bearish } label: { Label("dashboard.filter.bearish", systemImage: "arrow.down.right") }
            Button { viewModel.filterMode = .bullish } label: { Label("dashboard.filter.bullish", systemImage: "arrow.up.right") }
        } label: {
            Image(systemName: "line.3.horizontal.decrease.circle")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(Color.Alpha.brand)
        }
    }

    private var sectionHeaderView: some View {
        HStack(alignment: .lastTextBaseline) {
            Text("dashboard.section.recent_news")
                .font(.system(size: 13, weight: .bold))
                .textCase(.uppercase)
                .kerning(1.5)
                .foregroundStyle(Color.Alpha.taupe)
            
            Spacer()
            
            Button {
                // Action
            } label: {
                Text("common.action.view_all")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Color.Alpha.brand)
            }
            
            searchAndFilterBar
                .padding(.leading, 8)
        }
        .padding(.horizontal)
    }

    private var utcDateFormatter: DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        formatter.timeZone = TimeZone(abbreviation: "UTC")
        return formatter
    }

    private var statusColor: Color {
        switch viewModel.connectionStatus {
        case "dashboard.connection.live":
            return Color.Alpha.up
        case "dashboard.connection.connecting":
            return Color.Alpha.brand
        default:
            return Color.Alpha.down
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
        .font(.system(size: 12, weight: .medium, design: .monospaced))
        .foregroundStyle(.gray.opacity(0.5))
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
            .foregroundStyle(mode == .bullish ? Color.Alpha.up : Color.Alpha.down)
            
            Text(LocalizedStringKey(mode == .bullish ? "dashboard.correlation.bullish_desc" : "dashboard.correlation.bearish_desc"))
                .font(.caption)
                .foregroundStyle(Color.Alpha.textSecondary)
            
            Divider().background(Color.Alpha.separator).padding(.vertical, 8)
        }
        .padding(.bottom, 8)
    }
    
    @ViewBuilder
    private func timelineItem(item: IntelligenceItem, isLast: Bool) -> some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(spacing: 0) {
                Circle()
                    .fill(item.urgencyScore >= 8 ? Color.Alpha.down : Color.Alpha.brand)
                    .frame(width: 10, height: 10)
                    .overlay(
                        Circle().stroke(Color.Alpha.surface, lineWidth: 2)
                    )

                if !isLast {
                    Rectangle()
                        .fill(Color.Alpha.separator)
                        .frame(width: 2)
                        .padding(.vertical, 4)
                }
            }
            .padding(.top, 15)

            VStack {
                NavigationLink(destination: IntelligenceDetailView(item: item)) {
                    IntelligenceItemCard(item: item, style: .standard)
                }
                .buttonStyle(LiquidScaleButtonStyle())
            }
            .padding(.bottom, isLast ? 0 : 20)
        }
    }

    private func sentimentColor(_ sentiment: String) -> Color {
        switch sentiment {
        case "bullish": return Color.Alpha.up
        case "bearish": return Color.Alpha.down
        default: return Color.Alpha.neutral
        }
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
