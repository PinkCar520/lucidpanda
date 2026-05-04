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
    @State private var isDeepAnalysisPresented = false
    @State private var selectedItem: IntelligenceItem?

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
                    List {
                        let displayItems = viewModel.items.isEmpty ? cachedItems.map { IntelligenceItem(from: $0) } : viewModel.filteredItems

                        if displayItems.isEmpty {
                            emptyStateView
                                .listRowInsets(EdgeInsets())
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)
                                .padding(.top, 100)
                        } else {
                            // 2. Featured Analysis (Top item)
                            if let featured = displayItems.first {
                                Button {
                                    selectedItem = featured
                                } label: {
                                    IntelligenceItemCard(item: featured, style: .featured)
                                }
                                .buttonStyle(LiquidScaleButtonStyle())
                                .listRowInsets(EdgeInsets(top: 20, leading: 16, bottom: 20, trailing: 16))
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)
                            }

                            // 3. News Section (Title & List) - Exact Original Layout
                            sectionHeaderView
                                .padding(.vertical, 16)
                                .listRowInsets(EdgeInsets()) // Neutralize List row padding
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)

                            ForEach(Array(displayItems.dropFirst().enumerated()), id: \.element.id) { index, item in
                                Button {
                                    selectedItem = item
                                } label: {
                                    IntelligenceItemCard(item: item, style: .standard)
                                }
                                .buttonStyle(LiquidScaleButtonStyle())
                                .padding(.horizontal) // Match original container padding
                            }
                            .listRowInsets(EdgeInsets(top: 6, leading: 0, bottom: 6, trailing: 0))
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                        }
                        
                        Color.clear.frame(height: 100)
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                    .refreshable {
                        await viewModel.startIntelligenceStream()
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(item: $selectedItem) { item in
                IntelligenceDetailView(item: item)
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    // Button 1: Real-time Market Status & Label
                    Button {
                        let generator = UIImpactFeedbackGenerator(style: .medium)
                        generator.impactOccurred()
                        isPulseSheetPresented = true
                    } label: {
                        let sentimentColor: Color = {
                            guard let pulse = rootViewModel.marketPulseViewModel.pulseData else { return Color.Alpha.brand }
                            switch pulse.overallSentiment {
                            case "bullish": return Color.Alpha.up
                            case "bearish": return Color.Alpha.down
                            default: return Color.Alpha.brand
                            }
                        }()
                        
                        HStack(spacing: 8) {
                            Circle()
                                .fill(sentimentColor)
                                .frame(width: 8, height: 8)
                                .opacity(isTickerAnimating ? 1 : 0.3)
                                .scaleEffect(isTickerAnimating ? 1.2 : 0.8)
                                .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: isTickerAnimating)
                            
                            let sentimentText: String = {
                                if let pulse = rootViewModel.marketPulseViewModel.pulseData {
                                    return "\(pulse.overallSentimentZh) \(String(format: "%.2f", pulse.sentimentScore))"
                                }
                                return String(localized: "dashboard.asset.gold.live_label")
                            }()
                            
                            Text(sentimentText)
                                .font(.system(size: 13, weight: .semibold, design: .monospaced))
                                .foregroundStyle(sentimentColor)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                    }
                    .buttonStyle(.plain)
                    .onAppear { isTickerAnimating = true }
                    .fixedSize(horizontal: true, vertical: false)
                }
                
                ToolbarSpacer(.fixed)

                ToolbarItem {
                    // Button 2: Numerical Data (Price & Change)
                    Button {
                        let generator = UIImpactFeedbackGenerator(style: .light)
                        generator.impactOccurred()
                        isDeepAnalysisPresented = true
                    } label: {
                        HStack(spacing: 8) {
                            HStack(spacing: 2) {
                                Text(verbatim: "$")
                                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                                
                                Text(String(format: "%.2f", rootViewModel.marketPulseViewModel.pulseData?.marketSnapshot.gold.price ?? 0.00))
                                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                                    .contentTransition(.numericText())
                            }
                            .foregroundStyle(Color.Alpha.textPrimary)
                            
                            let change = rootViewModel.marketPulseViewModel.pulseData?.marketSnapshot.gold.changePercent ?? 0.00
                            let formattedChange = Formatters.signedPercentFormatter(fractionDigits: 2).string(from: NSNumber(value: change / 100.0)) ?? "\(change.formatted(.number.precision(.fractionLength(2))))%"
                            Text(formattedChange)
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .padding(.horizontal, 4)
                                .padding(.vertical, 2)
                                .background(change >= 0 ? Color.Alpha.up.opacity(0.15) : Color.Alpha.down.opacity(0.15))
                                .foregroundStyle(change >= 0 ? Color.Alpha.up : Color.Alpha.down)
                                .clipShape(RoundedRectangle(cornerRadius: 4))
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .opacity(rootViewModel.marketPulseViewModel.pulseData == nil ? 0.3 : 1.0)
                    }
                    .buttonStyle(.plain)
                    .fixedSize(horizontal: true, vertical: false)
                    .disabled(rootViewModel.marketPulseViewModel.pulseData == nil)
                }

                ToolbarSpacer(.flexible)
                
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        isSettingsPresented = true
                    } label: {
                        if let avatarUrl = rootViewModel.userProfile?.avatarUrl, 
                           let absoluteUrl = URL(string: avatarUrl, relativeTo: APIClient.shared.baseURL) {
                            AsyncImage(url: absoluteUrl) { image in
                                image
                                    .resizable()
                                    .scaledToFill()
                            } placeholder: {
                                initialText
                            }
                            .frame(width: 28, height: 28)
                            .clipShape(Circle())
                        } else {
                            initialText
                        }
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
                .environment(rootViewModel) // 🚀 关键修复：显式注入环境对象防止 Sheet 内崩溃
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
        .sheet(isPresented: $isPulseSheetPresented) {
            MarketPulseSheet(viewModel: rootViewModel.marketPulseViewModel)
                .presentationDetents([PresentationDetent.fraction(0.7)])
                .presentationDragIndicator(Visibility.visible)
        }
        .sheet(isPresented: $isDeepAnalysisPresented) {
            GoldDeepAnalysisSheet()
                .presentationDetents([.fraction(0.95)])
                .presentationDragIndicator(Visibility.visible)
        }
    }
    
    @State private var isTickerAnimating = false

    private var initialText: some View {
        let displayEmail = rootViewModel.userProfile?.email ?? "root@lucidpanda.com"
        let initial = String(displayEmail.prefix(1)).uppercased()
        
        return Text(initial)
            .font(.system(size: 16, weight: .black))
            .foregroundStyle(Color.Alpha.brand)
            .frame(width: 28, height: 28)
    }

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
            
            searchAndFilterBar
                .padding(.leading, 8)
        }
        .padding(.horizontal)
    }

    private var utcDateFormatter: DateFormatter {
        Self.sharedUtcFormatter
    }
    
    private static let sharedUtcFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        formatter.timeZone = TimeZone(abbreviation: "UTC")
        return formatter
    }()

    private var statusColor: Color {
        switch viewModel.connectionStatus {
        case "dashboard.connection.live":
            return Color.Alpha.down
        case "dashboard.connection.connecting":
            return Color.Alpha.brand
        default:
            return Color.Alpha.up
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
                    .fill(item.urgencyScore >= 8 ? Color.Alpha.up : Color.Alpha.brand)
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
                Button {
                    selectedItem = item
                } label: {
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
    
    init(from related: FundRelatedIntelligence) {
        self.init(
            id: related.id,
            timestamp: related.timestamp,
            author: related.author ?? "Unknown",
            summary: related.summary,
            content: "", // Will be fetched on-demand in detail view
            sentiment: related.sentiment,
            urgencyScore: related.urgencyScore,
            goldPriceSnapshot: nil
        )
    }
}
