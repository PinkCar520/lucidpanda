import SwiftUI
import AlphaDesign
import AlphaData
import SwiftData

struct MainDashboardView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel = DashboardViewModel()
    @Environment(AppRootViewModel.self) private var rootViewModel
    
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
    }
    
    private var headerSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("战术驾驶舱")
                    .font(.system(size: 24, weight: .black, design: .rounded))
                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                
                HStack(spacing: 6) {
                    Circle()
                        .fill(viewModel.isStreaming ? .green : .red)
                        .frame(width: 6, height: 6)
                    
                    Text("信号同步: \(viewModel.connectionStatus)")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
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
            // 搜索框
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.gray)
                TextField("搜索情报关键词...", text: $viewModel.searchQuery)
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
                filterButton(title: "全部", mode: .all)
                filterButton(title: "评分 8+", mode: .essential)
                filterButton(title: "看跌信号", mode: .bearish)
            }
            .padding(.horizontal)
        }
    }
    
    private func filterButton(title: String, mode: DashboardViewModel.FilterMode) -> some View {
        Button {
            withAnimation(.spring(response: 0.3)) {
                viewModel.filterMode = mode
            }
        } label: {
            Text(title)
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
                Text("正在从后端提取情报...")
            } else {
                Image(systemName: "tray.and.arrow.down")
                    .font(.system(size: 40))
                    .foregroundStyle(.gray.opacity(0.2))
                Text("未找到匹配的情报")
            }
        }
        .font(.system(size: 12, weight: .bold, design: .monospaced))
        .foregroundStyle(.gray.opacity(0.5))
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
