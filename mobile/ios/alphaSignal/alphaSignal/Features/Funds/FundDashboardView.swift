import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore
import SwiftData

// MARK: - Group Manager Mode

enum GroupManagerMode {
    case filter       // 分组筛选（左上角按钮）
    case moveFund     // 移动基金（长按菜单）
}

private struct ScrollOffsetKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

private enum PanelState {
    case fund    // 基金优先
    case market  // 市场优先
}

struct FundDashboardView: View {
    @State private var viewModel = FundViewModel()
    @Environment(\.colorScheme) var colorScheme
    @Environment(\.modelContext) private var modelContext

    @State private var showGroupPicker = false
    @State private var pendingMoveFund: FundValuation?
    @State private var showDeleteConfirmation = false
    @State private var pendingDeleteFund: FundValuation?
    @State private var showCreateGroupSheet = false
    @State private var selectedGroupForFilter: String? = nil
    @State private var selectedFund: FundValuation?
    @State private var showFundDetail = false
    @State private var showGroupManager = false
    @State private var pendingMoveFundForManager: FundValuation?
    @State private var showCreateGroupOnly = false
    @State private var groupManagerMode: GroupManagerMode = .filter
    @State private var scrollOffset: CGFloat = 0
    @State private var panelState: PanelState = .fund
    @State private var dragTranslation: CGFloat = 0

    // 交互参数
    private let triggerDistance: CGFloat = 140
    private let stayFundBand: ClosedRange<CGFloat> = 0...80
    private let stayMarketBandLower: CGFloat = 120
    private let maxTravel: CGFloat = 220
    private let damping: CGFloat = 0.6
    private let snapDuration: CGFloat = 0.28
    private let velocityThreshold: CGFloat = 800
    private let minMarketHeight: CGFloat = 72
    private let maxMarketHeightRatio: CGFloat = 0.4

    // 示例文案/数值（数据接入前的占位）
    private let sampleHotSectors: [String] = ["半导体", "新能源", "医药"]
    private let sampleFlow: String = "+68亿"
    private let sampleRiseFall: String = "1.6 : 1"
    private let sampleInsight: String = "早盘科技回暖，北向净流入放缓"

    var body: some View {
        NavigationStack {
            dashboardContent
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { dashboardToolbar }
                .navigationDestination(isPresented: $showFundDetail) {
                    if let fund = selectedFund {
                        FundDetailView(valuation: fund)
                    }
                }
        }
        .modelContext(modelContext)
        .task {
            viewModel.setModelContext(modelContext)
            await viewModel.fetchWatchlist()
            await viewModel.fetchGroups()
        }
        .sheet(isPresented: $showCreateGroupOnly) {
            CreateGroupForm { name, icon, color in
                Task {
                    let sortIndex = viewModel.groups.count
                    await viewModel.createGroup(name: name, icon: icon, color: color, sortIndex: sortIndex)
                }
            }
        }
        .sheet(isPresented: $showGroupManager) {
            GroupManagerView(
                groups: viewModel.groups,
                selectedGroupId: groupManagerMode == .filter ? selectedGroupForFilter : nil,
                mode: groupManagerMode
            ) { groupId in
                if groupManagerMode == .moveFund, let fund = pendingMoveFundForManager {
                    Task {
                        await viewModel.moveFundToGroup(code: fund.fundCode, groupId: groupId)
                    }
                } else {
                    withAnimation(.spring()) {
                        selectedGroupForFilter = groupId
                        if let groupId = groupId {
                            viewModel.viewMode = .group(groupId)
                        } else {
                            viewModel.viewMode = .all
                        }
                    }
                }
            } onDeleteGroup: { groupId in
                Task {
                    await viewModel.deleteGroup(groupId: groupId)
                }
            }
        }
        .overlay { deleteUndoOverlay }
        .alert("删除基金", isPresented: $showDeleteConfirmation) {
            Button("取消", role: .cancel) { }
            Button("删除", role: .destructive) {
                if let fund = pendingDeleteFund {
                    Task {
                        await viewModel.deleteFund(code: fund.fundCode)
                    }
                }
            }
        } message: {
            if let fund = pendingDeleteFund {
                Text("确定要从自选列表中删除「\(fund.fundName)」吗？此操作可以撤销。")
            }
        }
    }

    // MARK: - Subviews

    private var dashboardContent: some View {
        GeometryReader { proxy in
            let spacing: CGFloat = 12
            let maxMarketHeight = max(minMarketHeight, proxy.size.height * maxMarketHeightRatio)
            let collapseDistance = max(1, maxMarketHeight - minMarketHeight)
            let clampedOffset = min(0, scrollOffset)
            let collapseProgress = min(1, (-clampedOffset) / collapseDistance)

            let effectiveDrag = min(maxTravel, max(0, -clampedOffset + dragTranslation)) * damping
            let marketHeight = max(minMarketHeight, min(maxMarketHeight, maxMarketHeight - collapseDistance * collapseProgress + effectiveDrag))
            let visualProgress = min(1, (effectiveDrag + (-clampedOffset)) / triggerDistance)
            
            // 更强力、更直接的连续视差：直接使用 scrollOffset，让底层以接近列表的速度（0.8倍）被往上顶走
            let marketParallaxOffset = scrollOffset < 0 ? scrollOffset * 0.85 : 0
            
            let topPadding = maxMarketHeight + spacing
            let bottomPadding: CGFloat = 16
            let minWatchlistHeight = max(0, proxy.size.height - topPadding - bottomPadding)

            ZStack(alignment: .top) {
                LiquidBackground()
                marketLayer(height: marketHeight, collapseProgress: collapseProgress, visualProgress: visualProgress)
                    .offset(y: marketParallaxOffset) 
                    .padding(.top, 12)
                    .padding(.horizontal)

                ScrollView(showsIndicators: false) {
                    GeometryReader { geo in
                        Color.clear.preference(key: ScrollOffsetKey.self, value: geo.frame(in: .named("fundsScroll")).minY)
                    }
                    .frame(height: 0)

                    watchlistPanel(minHeight: minWatchlistHeight)
                        .padding(.top, topPadding)
                        .padding(.bottom, bottomPadding)
                }
                .coordinateSpace(name: "fundsScroll")
                .gesture(dragGesture)
                .onPreferenceChange(ScrollOffsetKey.self) { value in
                    scrollOffset = value
                }
                .refreshable {
                    await viewModel.fetchWatchlist()
                }
            }
        }
    }

    @ViewBuilder
    private func marketLayer(height: CGFloat, collapseProgress: CGFloat, visualProgress: CGFloat) -> some View {
        let detailOpacity = max(0, 1 - collapseProgress * 1.1)
        let panelScale = 1.0 - (collapseProgress * 0.04)
        let panelBlur = collapseProgress * 3.0
        let parallaxOffset = -collapseProgress * 80

        VStack(spacing: 12) {
            marketSummaryBar
                .zIndex(1) // 确保在上方
            if detailOpacity > 0.01 {
                marketDetailPanel
                    .opacity(detailOpacity)
                    .scaleEffect(panelScale, anchor: .top)
                    .blur(radius: panelBlur)
                    .offset(y: parallaxOffset)
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
            Spacer(minLength: 0)
        }
        .frame(height: height, alignment: .top)
        .clipped()
        .animation(.spring(response: 0.35, dampingFraction: 0.85), value: panelState)
        .onChange(of: panelState) { _ in
            // 触觉反馈在状态切换时触发
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
        }
    }

    @ViewBuilder
    private var filterChips: some View {
        if !viewModel.groups.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    FilterChip(
                        title: "全部",
                        isSelected: selectedGroupForFilter == nil
                    ) {
                        withAnimation(.spring()) {
                            selectedGroupForFilter = nil
                            viewModel.viewMode = .all
                        }
                    }

                    ForEach(viewModel.groups) { group in
                        FilterChip(
                            title: group.name,
                            color: Color(hex: group.color),
                            isSelected: selectedGroupForFilter == group.id
                        ) {
                            withAnimation(.spring()) {
                                selectedGroupForFilter = group.id
                                viewModel.viewMode = .group(group.id)
                            }
                        }
                    }
                }
            }
            .frame(height: 56) // 稍微变大以容纳更大的 Chip
        }
    }

    private func watchlistPanel(minHeight: CGFloat) -> some View {
        VStack(spacing: 0) {
            listSection
        }
        .frame(maxWidth: .infinity, minHeight: minHeight, alignment: .top)
        .background(Color(uiColor: .systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .shadow(color: .black.opacity(0.06), radius: 16, x: 0, y: -4)
        .opacity(panelState == .market ? 0.6 : 1)
        .scaleEffect(panelState == .market ? 0.96 : 1)
    }

    private var marketSummaryBar: some View {
        HStack(spacing: 10) {
            marketSummaryPill(title: "上证", value: "—", trend: .neutral)
            marketSummaryPill(title: "深证", value: "—", trend: .neutral)
            marketSummaryPill(title: "创业板", value: "—", trend: .neutral)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        // 移除多余的描边和厚重材质，保持底层通透
        .background(Color.white.opacity(0.15))
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var marketDetailPanel: some View {
        VStack(spacing: 12) {
            // 热门板块 + 资金/涨跌比
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("市场全景")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(.primary)
                    Spacer()
                    Text("实盘刷新中")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(.secondary)
                }

                HStack(spacing: 12) {
                    marketMetric(title: "热门板块", value: sampleHotSectors.prefix(3).joined(separator: " · "))
                    marketMetric(title: "资金流向", value: sampleFlow)
                    marketMetric(title: "涨跌比", value: sampleRiseFall)
                }
            }
            .padding(16)
            .background(Color.white.opacity(0.6))
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        }
    }

    private enum MarketTrend {
        case up
        case down
        case neutral
    }

    private func marketSummaryPill(title: String, value: String, trend: MarketTrend) -> some View {
        HStack(spacing: 6) {
            Text(title)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(trend == .up ? .red : trend == .down ? .green : .secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(Color.black.opacity(0.04))
        .clipShape(Capsule())
    }

    private func marketMetric(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .foregroundStyle(.primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Color.black.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    

    private var listSection: some View {
        LazyVStack(spacing: 16, pinnedViews: [.sectionHeaders]) {
            Section(header: filterChipsHeader) {
                if viewModel.watchlist.isEmpty && !viewModel.isLoading {
                    emptyStateView
                        .padding(.horizontal)
                } else {
                    ForEach(viewModel.sortedWatchlist) { valuation in
                        SwipeToDeleteCell {
                            pendingDeleteFund = valuation
                            showDeleteConfirmation = true
                        } content: {
                            Button {
                                selectedFund = valuation
                                showFundDetail = true
                            } label: {
                                FundCompactCard(valuation: valuation)
                            }
                            .buttonStyle(.plain)
                            .contextMenu {
                                Button {
                                    pendingMoveFundForManager = valuation
                                    groupManagerMode = .moveFund
                                    showGroupManager = true
                                } label: {
                                    Label("移动分组", systemImage: "folder.badge.plus")
                                }

                                Divider()

                                Button(role: .destructive) {
                                    pendingDeleteFund = valuation
                                    showDeleteConfirmation = true
                                } label: {
                                    Label("删除", systemImage: "trash")
                                }
                            }
                        }
                        .padding(.horizontal)
                    }
                }

                Spacer(minLength: 100)
            }
        }
    }

    // MARK: - Gesture

    private var dragGesture: some Gesture {
        DragGesture()
            .onChanged { value in
                // 仅在列表已到顶部时响应上拉，下拉则允许市场层回收
                let isAtTop = scrollOffset >= -1 // 容忍浮点误差
                let translation = value.translation.height

                if isAtTop {
                    if translation < 0 {
                        // 上拉，记录正向数值（向上为正）
                        dragTranslation = min(maxTravel, -translation)
                    } else {
                        // 下拉：允许从市场态回到基金态
                        dragTranslation = -min(maxTravel, translation)
                    }
                } else {
                    dragTranslation = 0
                }
            }
            .onEnded { value in
                let velocity = value.velocity.height // 正下负上（SwiftUI 16+ 提供）
                let upwardVelocity = -velocity

                let finalState: PanelState

                if upwardVelocity >= velocityThreshold {
                    finalState = .market
                } else if velocity >= velocityThreshold {
                    finalState = .fund
                } else {
                    // 使用拖拽位移判定
                    let drag = max(0, dragTranslation)
                    if stayFundBand.contains(drag) {
                        finalState = .fund
                    } else if drag >= stayMarketBandLower {
                        finalState = .market
                    } else {
                        // 中间区间根据当前状态和阈值
                        finalState = drag >= triggerDistance ? .market : .fund
                    }
                }

                withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                    panelState = finalState
                    dragTranslation = 0
                }
            }
    }

    @ViewBuilder
    private var filterChipsHeader: some View {
        if !viewModel.groups.isEmpty {
            VStack(alignment: .leading, spacing: 0) {
                filterChips
            }
            .padding(.horizontal)
            .padding(.top, 16)
            .padding(.bottom, 12)
        }
    }

    @ToolbarContentBuilder
    private var dashboardToolbar: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            Button {
                showCreateGroupOnly = true
            } label: {
                Image(systemName: "folder.badge.plus")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.primary)
            }
        }
        
        ToolbarItem(placement: .topBarTrailing) {
            Button {
                withAnimation(.spring()) {
                    viewModel.toggleSortOrder()
                }
            } label: {
                Image(systemName: viewModel.sortOrder.icon)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(.blue)
            }
        }
    }

    @ViewBuilder
    private var deleteUndoOverlay: some View {
        if let deletedFund = viewModel.lastDeletedFund {
            VStack {
                Spacer()
                HStack {
                    Text("已删除「\(deletedFund.fund.fundName)」")
                        .font(.subheadline)
                    Spacer()
                    Button("撤销") {
                        Task {
                            await viewModel.undoDelete()
                        }
                    }
                    .buttonStyle(.bordered)
                    .tint(.blue)
                }
                .padding()
                .background(.ultraThickMaterial)
                .cornerRadius(12)
                .padding()
            }
            .transition(.move(edge: .bottom))
        }
    }
    
    private var emptyStateView: some View {
        LiquidGlassCard {
            VStack(spacing: 20) {
                Spacer(minLength: 100)
                Image(systemName: "chart.line.uptrend.xyaxis")
                    .font(.system(size: 48))
                    .foregroundStyle(.gray.opacity(0.2))
                Text("funds.empty.title")
                    .font(.headline)
                    .foregroundStyle(.gray)
                Text("funds.empty.hint")
                    .font(.subheadline)
                    .foregroundStyle(.blue)
                Text("请使用底部搜索添加基金")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                
                Spacer()
            }
        }
    }
    
}

// MARK: - Filter Chip

struct FilterChip: View {
    let title: String
    var color: Color? = nil
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 16, weight: .bold)) // 增大字号 15 -> 16
                .padding(.horizontal, 22) // 增大横向间距 20 -> 22
                .padding(.vertical, 12)   // 增大垂直间距 10 -> 12
                .foregroundStyle(isSelected ? (color ?? .blue) : .primary)
                .glassEffect(.regular, in: .capsule)
                .clipShape(Capsule())
        }
    }
}

// MARK: - Group Manager (统一分组管理：选择 + 新建)

struct GroupManagerView: View {
    let groups: [WatchlistGroup]
    let selectedGroupId: String?
    let mode: GroupManagerMode
    let onSelect: (String?) -> Void
    let onDeleteGroup: (String) -> Void
    
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
//                LiquidBackground()
                
                List {
                    // 分组列表
                    Section {
                        ForEach(groups) { group in
                            Button {
                                onSelect(group.id)
                                dismiss()
                            } label: {
                                HStack {
                                    Text(group.name)
                                        .foregroundStyle(.primary)
                                    Spacer()
                                    if selectedGroupId == group.id {
                                        Image(systemName: "checkmark")
                                            .foregroundStyle(.blue)
                                    }
                                }
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    onDeleteGroup(group.id)
                                } label: {
                                    Label("删除", systemImage: "trash")
                                }
                            }
                        }
                    }
                    
                    // 移动分组模式：显示"全部"选项
                    if mode == .moveFund {
                        Section {
                            Button {
                                onSelect(nil)
                                dismiss()
                            } label: {
                                HStack {
                                    Text("全部")
                                        .foregroundStyle(.primary)
                                    Spacer()
                                    if selectedGroupId == nil {
                                        Image(systemName: "checkmark")
                                            .foregroundStyle(.blue)
                                    }
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle(mode == .filter ? "分组管理" : "移动分组到")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
            }
            .presentationDetents(mode == .filter ? [.large] : [.medium])
            .presentationDragIndicator(mode == .filter ? .hidden : .visible)
        }
    }
}

// MARK: - Create Group Form (内联创建分组表单)

struct CreateGroupForm: View {
    @State private var groupName = ""
    @FocusState private var isGroupNameFocused: Bool
    @Environment(\.dismiss) var dismiss

    let onCreate: (String, String, String) -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("分组名称") {
                    TextField("如：科技基金、QDII", text: $groupName)
                        .autocapitalization(.none)
                        .focused($isGroupNameFocused)
                }
            }
            .navigationTitle("新建分组")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        onCreate(groupName, "folder.badge.plus", "#007AFF")
                        dismiss()
                    } label: {
                        Image(systemName: "checkmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.blue)
                    }
                }
            }
            .task {
                isGroupNameFocused = true
            }
        }
    }
}

// MARK: - Safe Horizontal Swipe To Delete

struct SwipeToDeleteCell<Content: View>: View {
    let onDelete: () -> Void
    let content: () -> Content

    @State private var offset: CGFloat = 0
    @State private var isSwiped = false
    @State private var lockDirection: Bool = false
    private let buttonWidth: CGFloat = 80

    var body: some View {
        ZStack(alignment: .trailing) {
            Button {
                withAnimation(.spring()) { offset = 0; isSwiped = false }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { onDelete() }
            } label: {
                VStack {
                    Image(systemName: "trash")
                        .font(.system(size: 18, weight: .semibold))
                    Text("删除")
                        .font(.system(size: 12, weight: .medium))
                        .padding(.top, 4)
                }
                .frame(width: buttonWidth)
                .frame(maxHeight: .infinity)
                .background(Color.red)
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
            .padding(.vertical, 0)
            .opacity(offset < -5 ? 1 : 0)

            content()
                .background(Color(uiColor: .systemBackground))
                .offset(x: offset)
                .gesture(
                    DragGesture(minimumDistance: 15, coordinateSpace: .local)
                        .onChanged { value in
                            if !lockDirection {
                                if abs(value.translation.width) > abs(value.translation.height) {
                                    lockDirection = true
                                } else {
                                    return
                                }
                            }
                            guard lockDirection else { return }

                            let currentX = value.translation.width
                            if currentX < 0 {
                                offset = isSwiped ? max(currentX - buttonWidth, -buttonWidth * 1.5) : max(currentX, -buttonWidth * 1.5)
                            } else if isSwiped {
                                offset = min(0, currentX - buttonWidth)
                            }
                        }
                        .onEnded { value in
                            lockDirection = false
                            withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                                if value.translation.width < -buttonWidth / 2 || value.predictedEndTranslation.width < -buttonWidth {
                                    offset = -buttonWidth
                                    isSwiped = true
                                    UIImpactFeedbackGenerator(style: .medium).impactOccurred()
                                } else {
                                    offset = 0
                                    isSwiped = false
                                }
                            }
                        }
                )
        }
    }
}
