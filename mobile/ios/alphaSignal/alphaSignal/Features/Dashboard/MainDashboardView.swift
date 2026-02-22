import SwiftUI
import AlphaDesign
import AlphaData
import SwiftData

struct MainDashboardView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel = DashboardViewModel()
    @Environment(AppRootViewModel.self) private var rootViewModel
    @State private var isSettingsPresented = false
    
    @Query(sort: \IntelligenceModel.timestamp, order: .reverse) 
    private var cachedItems: [IntelligenceModel]
    
    var body: some View {
        @Bindable var viewModel = viewModel
        return NavigationStack {
            ZStack {
                LiquidBackground()

                VStack(spacing: 0) {
                    // 1. 顶部状态栏
                    headerSection

                    // 2. 搜索与过滤器 (对齐 Web 端)
                    searchAndFilterBar
                    

                    
                    ScrollView(showsIndicators: false) {
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
                        ZStack {
                            Circle()
                                .fill(Color(uiColor: .secondarySystemFill))
                                .frame(width: 36, height: 36)
                            Circle()
                                .strokeBorder(.quaternary)
                                .frame(width: 36, height: 36)
                            Text("A")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(.primary)
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
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("dashboard.title")
                    .font(.title2.weight(.bold))
                    .foregroundStyle(.primary)

                HStack(spacing: 6) {
                    Circle()
                        .fill(viewModel.isStreaming ? .green : .red)
                        .frame(width: 6, height: 6)

                    Text("\(t("dashboard.realtime_status")): \(t(viewModel.connectionStatus))")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(viewModel.isStreaming ? .green : .red)
                        .opacity(0.8)
                }
            }
            Spacer()
        }
        .padding(.horizontal)
        .padding(.top, 24)
        .padding(.bottom, 16)
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
                .foregroundStyle(viewModel.filterMode == mode ? .primary : .secondary)
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
