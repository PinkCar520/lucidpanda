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
                            let displayItems = viewModel.items.isEmpty ? cachedItems.map { IntelligenceItem(model: $0) } : viewModel.filteredItems

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
        }
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
                    .font(.system(size: 24, weight: .black, design: .rounded))
                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                
                HStack(spacing: 6) {
                    Circle()
                        .fill(viewModel.isStreaming ? .green : .red)
                        .frame(width: 6, height: 6)
                    
                    Text("\(t("dashboard.realtime_status")): \(t(viewModel.connectionStatus))")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundStyle(viewModel.isStreaming ? .green : .red)
                        .opacity(0.8)
                }
            }
            Spacer()
            Button {
                isSettingsPresented = true
            } label: {
                Circle()
                    .fill(Color.blue.opacity(0.2))
                    .frame(width: 36, height: 36)
                    .overlay(
                        Text("A")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(.blue)
                    )
            }
            .buttonStyle(.plain)
            .accessibilityLabel(Text("dashboard.action.open_settings"))
        }
        .padding(.horizontal)
        .padding(.top, 24)
        .padding(.bottom, 16)
    }
    
    private var searchAndFilterBar: some View {
        VStack(spacing: 12) {
            // 搜索框
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.gray)
                TextField(t("dashboard.search.placeholder"), text: $viewModel.searchQuery)
                    .font(.subheadline)
                if !viewModel.searchQuery.isEmpty {
                    Button { viewModel.searchQuery = "" } label: {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(.gray)
                    }
                }
            }
            .padding(10)
            .background(Color.black.opacity(0.03))
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .padding(.horizontal)
            
            // 过滤器切换
            HStack(spacing: 8) {
                filterButton(titleKey: "dashboard.filter.all", mode: .all)
                filterButton(titleKey: "dashboard.filter.score8", mode: .essential)
                filterButton(titleKey: "dashboard.filter.bearish", mode: .bearish)
            }
            .padding(.horizontal)
        }
    }
    
    private func filterButton(titleKey: String, mode: DashboardViewModel.FilterMode) -> some View {
        Button {
            withAnimation(.spring(response: 0.3)) {
                viewModel.filterMode = mode
            }
        } label: {
            Text(t(titleKey))
                .font(.system(size: 10, weight: .bold))
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(viewModel.filterMode == mode ? Color.blue : Color.black.opacity(0.03))
                .foregroundStyle(viewModel.filterMode == mode ? .white : .gray)
                .clipShape(Capsule())
        }
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Spacer(minLength: 100)
            if viewModel.items.isEmpty && viewModel.isStreaming {
                ProgressView().tint(.blue)
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
    init(model: IntelligenceModel) {
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
