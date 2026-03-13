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
    @State private var isPulseSheetPresented = false

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
                        // 1. 顶部状态栏 (Active Alerts | MARKET PULSE)
                        headerSection
                            .padding(.bottom, 16)

                        // 2. 搜索与过滤器
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

                // 2. 市场脉搏 (Market Pulse) & UTC Time - Integrated Button
                Button(action: {
                    let generator = UIImpactFeedbackGenerator(style: .medium)
                    generator.impactOccurred()
                    isPulseSheetPresented = true
                }) {
                    VStack(alignment: .leading, spacing: 0) {
                        HStack(spacing: 6) {
                            Circle()
                                .fill(statusColor)
                                .frame(width: 8, height: 8)

                            Text("MARKET PULSE")
                                .font(.system(size: 10, weight: .black, design: .monospaced))
                                .foregroundStyle(.primary)
                            
                            if let data = rootViewModel.marketPulseViewModel.pulseData {
                                Text(data.overallSentimentZh)
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundStyle(sentimentColor(data.overallSentiment))
                            }
                            
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
                }
                .buttonStyle(PlainButtonStyle())
                .frame(height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .shadow(color: .black.opacity(0.04), radius: 6, x: 0, y: 2)
            }
        }
        .padding(.horizontal)
        .padding(.top, 24)
        .sheet(isPresented: $isPulseSheetPresented) {
            MarketPulseSheet(viewModel: rootViewModel.marketPulseViewModel)
                .presentationDetents([.fraction(0.7)])
                .presentationDragIndicator(.visible)
        }
        .onReceive(timer) { input in
            currentTime = input
        }
    }

    private var utcDateFormatter: DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        formatter.timeZone = TimeZone(abbreviation: "UTC")
        return formatter
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
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    filterButton(titleKey: "dashboard.filter.all", mode: .all)
                    filterButton(titleKey: "dashboard.filter.score8", mode: .essential)
                    filterButton(titleKey: "dashboard.filter.bearish", mode: .bearish)
                    filterButton(titleKey: "dashboard.filter.bullish", mode: .bullish)
                }
                .padding(.horizontal)
            }
            .frame(height: 50)
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
                .foregroundStyle(.secondary)
            
            Divider().padding(.vertical, 8)
        }
        .padding(.bottom, 8)
    }
    
    @ViewBuilder
    private func timelineItem(item: IntelligenceItem, isLast: Bool) -> some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(spacing: 0) {
                Circle()
                    .fill(item.urgencyScore >= 8 ? Color.Alpha.down : Color.Alpha.primary)
                    .frame(width: 10, height: 10)
                    .overlay(
                        Circle().stroke(Color.Alpha.surface, lineWidth: 2)
                    )
                    .shadow(color: (item.urgencyScore >= 8 ? Color.Alpha.down : Color.Alpha.primary).opacity(0.3), radius: 4)

                if !isLast {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(width: 2)
                        .padding(.vertical, 4)
                }
            }
            .padding(.top, 15)

            VStack {
                NavigationLink(destination: IntelligenceDetailView(item: item)) {
                    IntelligenceItemCard(item: item)
                }
                .buttonStyle(LiquidScaleButtonStyle())
            }
            .padding(.bottom, isLast ? 0 : 20)
        }
    }

    private func sentimentColor(_ sentiment: String) -> Color {
        switch sentiment {
        case "bullish": return Color.Alpha.down
        case "bearish": return Color.Alpha.up
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
