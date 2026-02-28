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

                        // 2. 搜索与过滤器 (对齐 Web 端)
                        searchAndFilterBar

                        VStack(spacing: 16) {
                            let displayItems = viewModel.items.isEmpty ? cachedItems.map { IntelligenceItem(from: $0) } : viewModel.filteredItems

                            if displayItems.isEmpty {
                                emptyStateView
                            } else {
                                LazyVStack(spacing: 16) {
                                    ForEach(displayItems) { item in
                                        NavigationLink(destination: IntelligenceDetailView(item: item)) {
                                            IntelligenceItemCard(item: item)
                                        }
                                        .buttonStyle(.plain)
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
                        
                        ZStack {
                            if let avatarUrl = rootViewModel.userProfile?.avatarUrl {
                                let absoluteUrl = URL(string: avatarUrl, relativeTo: APIClient.shared.baseURL)
                                AsyncImage(url: absoluteUrl) { image in
                                    image
                                        .resizable()
                                        .scaledToFill()
                                } placeholder: {
                                    Circle().fill(Color(uiColor: .systemFill))
                                }
                                .frame(width: 32, height: 32)
                                .clipShape(Circle())
                                .overlay(
                                    Circle().strokeBorder(.quaternary)
                                )
                                .glassEffect(.clear.interactive())
                            } else {
                                Circle()
                                    .fill(Color(uiColor: .secondarySystemFill))
                                    .frame(width: 36, height: 36)
                                Circle()
                                    .strokeBorder(.quaternary)
                                    .frame(width: 36, height: 36)
                                Text(initial)
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(.primary)
                            }
                        }
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
                    Text("活跃警报")
                        .font(.system(size: 10, weight: .bold))
                        .textCase(.uppercase)
                        .foregroundStyle(.secondary)
                    
                    Text("\(activeAlertsCount)")
                        .font(.system(size: 22, weight: .black, design: .monospaced))
                        .foregroundStyle(activeAlertsCount > 0 ? .red : .primary)
                }
                .frame(width: 80, height: 64)
                .background(Color(uiColor: .secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                
                // 2. 实时状态 & UTC (Real-time Status & UTC Time)
                VStack(alignment: .leading, spacing: 0) {
                    HStack {
                        Circle()
                            .fill(viewModel.isStreaming ? .green : .red)
                            .frame(width: 8, height: 8)
                            
                        Text(viewModel.isStreaming ? "System Operational" : "System Degraded")
                            .font(.system(size: 12, weight: .bold, design: .monospaced))
                            .foregroundStyle(viewModel.isStreaming ? .green : .red)
                        Spacer()
                    }
                    .padding(.horizontal, 12)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(viewModel.isStreaming ? Color.green.opacity(0.1) : Color.red.opacity(0.1))
                    
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
                    .background(Color(uiColor: .secondarySystemBackground))
                }
                .frame(height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .stroke(Color(uiColor: .separator).opacity(0.3), lineWidth: 0.5)
                )
            }
        }
        .padding(.horizontal)
        .padding(.top, 24)
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
            Text(t(titleKey))
                .font(.system(size: 14, weight: .bold))
                .padding(.horizontal, 28)
                .padding(.vertical, 14)
                .foregroundStyle(viewModel.filterMode == mode ? Color.black : Color.secondary)
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
