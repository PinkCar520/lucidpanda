import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore
import SwiftData
import OSLog

// MARK: - Group Manager Mode

enum GroupManagerMode {
    case filter       // 分组筛选（左上角按钮）
    case moveFund     // 移动基金（长按菜单）
}

struct FundDashboardView: View {
    @State private var viewModel = FundViewModel()
    @Environment(\.colorScheme) var colorScheme
    @Environment(\.modelContext) private var modelContext

    // MARK: - Offline-First: @Query 直连 SwiftData，与 MainDashboardView 对称
    // View 渲染瞬间同步读取本地 SQLite，完全不依赖网络
    @Query(sort: \LocalWatchlistItem.sortIndex, order: .forward)
    private var cachedItems: [LocalWatchlistItem]

    @Query(sort: \LocalWatchlistGroup.sortIndex, order: .forward)
    private var cachedGroups: [LocalWatchlistGroup]

    @State private var showGroupPicker = false
    @State private var pendingMoveFund: FundValuation?
    @State private var showDeleteConfirmation = false
    @State private var pendingDeleteFund: FundValuation?
    @State private var showCreateGroupSheet = false
    @State private var navigationFund: FundValuation?

    @State private var showGroupManager = false
    @State private var pendingMoveFundForManager: FundValuation?
    @State private var showCreateGroupOnly = false
    @State private var groupManagerMode: GroupManagerMode = .filter
    @State private var scrollOffset: CGFloat = 0

    // 从 SwiftData 本地缓存 blob 恢复 FundValuation，用于网络不可达时的降级展示
    private var cachedValuations: [FundValuation] {
        cachedItems
            .filter { !$0.isDeleted }
            .compactMap { item -> FundValuation? in
                guard let data = item.cachedValuationData else { return nil }
                return try? JSONDecoder().decode(FundValuation.self, from: data)
            }
    }

    // 降级：网络数据优先，为空时用本地缓存（与 MainDashboardView 的策略对称）
    private var displayList: [FundValuation] {
        viewModel.watchlist.isEmpty ? cachedValuations : viewModel.sortedWatchlist
    }

    // 降级：网络分组优先，为空时用本地缓存
    private var displayGroups: [WatchlistGroup] {
        if !viewModel.groups.isEmpty { return viewModel.groups }
        return cachedGroups.map {
            WatchlistGroup(
                id: $0.id,
                userId: "",
                name: $0.name,
                icon: $0.icon,
                color: $0.color,
                sortIndex: Int($0.sortIndex),
                createdAt: $0.lastSyncTime,
                updatedAt: $0.lastSyncTime
            )
        }
    }

    var body: some View {
        @Bindable var viewModel = viewModel
        return NavigationStack {
            dashboardContent
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { dashboardToolbar }
                .toolbar(removing: .title)
        }
        .modelContext(modelContext)
        .task {
            viewModel.setModelContext(modelContext)
            await viewModel.fetchWatchlist()
            await viewModel.fetchGroups()
        }
        .onAppear {
            viewModel.startLiveUpdates()
        }
        .onDisappear {
            viewModel.stopLiveUpdates()
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
                selectedGroupId: groupManagerMode == .filter ? viewModel.selectedGroupId : nil,
                mode: groupManagerMode,
                onSelect: { groupId in
                    if groupManagerMode == .moveFund, let fund = pendingMoveFundForManager {
                        Task {
                            await viewModel.moveFundToGroup(code: fund.fundCode, groupId: groupId)
                        }
                    } else {
                        withAnimation(.spring()) {
                            if let groupId = groupId {
                                viewModel.viewMode = .group(groupId)
                            } else {
                                viewModel.viewMode = .all
                            }
                        }
                    }
                },
                onDeleteGroup: { groupId in
                    Task {
                        await viewModel.deleteGroup(groupId: groupId)
                    }
                },
                onMoveGroup: { indices, newOffset in
                    viewModel.reorderGroups(from: indices, to: newOffset)
                }
            )
        }
        .overlay { deleteUndoOverlay }
        .alert(Text(LocalizedStringKey("funds.delete.title")), isPresented: $showDeleteConfirmation) {
            Button("funds.action.cancel", role: .cancel) { }
            Button("funds.action.delete", role: .destructive) {
                if let fund = pendingDeleteFund {
                    Task {
                        await viewModel.deleteFund(code: fund.fundCode)
                    }
                }
            }
        } message: {
            if let fund = pendingDeleteFund {
                Text(String(format: String(localized: "funds.delete.confirm"), fund.fundName))
            }
        }
    }

    // MARK: - Subviews

    private var dashboardContent: some View {
        ZStack(alignment: .top) {
            Color.Alpha.background.ignoresSafeArea()

            VStack(spacing: 0) {
                // 顶部过滤器
                if !displayGroups.isEmpty {
                    filterChips
                        .background(.ultraThinMaterial)
                    
                    Divider().opacity(0.3)
                }

                List {
                    // Offline-First: 优先显示网络数据，网络不可达时降级到 @Query 本地缓存
                    // 真正无数据的判定：网络和本地缓存均为空，且不在加载中
                    if displayList.isEmpty && !viewModel.isLoading && cachedItems.isEmpty {
                        emptyStateView
                            .listRowInsets(EdgeInsets())
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                    } else {
                        ForEach(displayList) { valuation in
                            Button {
                                navigationFund = valuation
                            } label: {
                                FundCompactCard(
                                    valuation: valuation
                                )
                                .padding(.horizontal, 16)
                            }
                            .buttonStyle(.plain)
                            .listRowInsets(EdgeInsets(top: 8, leading: 0, bottom: 8, trailing: 0))
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    pendingDeleteFund = valuation
                                    showDeleteConfirmation = true
                                } label: {
                                    Label("funds.action.delete", systemImage: "trash")
                                }
                                .tint(.red)
                                
                                Button {
                                    pendingMoveFundForManager = valuation
                                    groupManagerMode = .moveFund
                                    showGroupManager = true
                                } label: {
                                    Label("funds.action.move", systemImage: "folder.badge.plus")
                                }
                                .tint(.blue)
                            }
                        }
                        
                        Text(LocalizedStringKey("funds.disclaimer"))
                            .font(.system(size: 11, weight: .regular))
                            .foregroundStyle(.secondary.opacity(0.8))
                            .multilineTextAlignment(.center)
                            .listRowInsets(EdgeInsets(top: 24, leading: 24, bottom: 40, trailing: 24))
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
                .refreshable {
                    await viewModel.fetchWatchlist()
                }
                .navigationDestination(item: $navigationFund) { valuation in
                    FundDetailView(valuation: valuation)
                }
            }
        }
    }

    @ViewBuilder
    private var filterChips: some View {
        if !displayGroups.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    FilterChip(
                        title: "funds.group.all",
                        isLocalizedKey: true,
                        isSelected: viewModel.viewMode == .all
                    ) {
                        withAnimation(.spring()) {
                            viewModel.viewMode = .all
                        }
                    }

                    ForEach(displayGroups) { group in
                        FilterChip(
                            title: group.name,
                            color: Color(hex: group.color),
                            isSelected: viewModel.selectedGroupId == group.id
                        ) {
                            withAnimation(.spring()) {
                                viewModel.viewMode = .group(group.id)
                            }
                        }
                    }
                }
                .padding(.horizontal, 16)
            }
            .frame(height: 56)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    @ToolbarContentBuilder
    private var dashboardToolbar: some ToolbarContent {
        ToolbarSpacer(.flexible)
        ToolbarItem() {
            Button {
                withAnimation(.spring()) {
                    viewModel.toggleSortOrder()
                }
            } label: {
                Image(systemName: viewModel.sortOrder.icon)
                    .accessibilityLabel(Text(viewModel.sortOrder.label))
                    .foregroundStyle(.primary)
            }
        }
        ToolbarSpacer(.fixed)
        ToolbarItem() {
            Menu {
                Button {
                    groupManagerMode = .filter
                    showGroupManager = true
                } label: {
                    Label(LocalizedStringKey("funds.group.manage_title"), systemImage: "line.3.horizontal")
                }

                Button {
                    showCreateGroupOnly = true
                } label: {
                    Label(LocalizedStringKey("funds.group.new"), systemImage: "folder.badge.plus")
                }
            } label: {
                ZStack {
                    Image(systemName: "ellipsis")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.primary)
                }
            }
        }
    }

    @ViewBuilder
    private var deleteUndoOverlay: some View {
        if let deletedFund = viewModel.lastDeletedFund {
            VStack {
                Spacer()
                HStack(spacing: 16) {
                    Image(systemName: "trash.fill")
                        .foregroundStyle(.white)
                        .font(.system(size: 14))
                        .padding(8)
                        .background(Color.red.opacity(0.6))
                        .clipShape(Circle())
                    
                    Text(String(format: String(localized: "funds.delete.success"), deletedFund.fund.fundName))
                        .font(.system(size: 14, weight: .medium))
                    
                    Spacer()
                    
                    Button {
                        Task {
                            await viewModel.undoDelete()
                        }
                    } label: {
                        Text("funds.action.undo")
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(.blue)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                            .glassEffect(.clear.interactive(), in: .capsule)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .glassEffect(.regular, in: .rect(cornerRadius: 16, style: .continuous))
                .padding(.horizontal, 20)
                .padding(.bottom, 24)
            }
            .transition(.move(edge: .bottom).combined(with: .opacity))
        }
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.line.uptrend.xyaxis")
                .font(.system(size: 48))
                .foregroundStyle(.gray.opacity(0.3))
            Text("funds.empty.title")
                .font(.headline)
                .foregroundStyle(.gray)
            Text("funds.empty.hint")
                .font(.subheadline)
                .foregroundStyle(.blue)
            Text("funds.empty_state")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .center)
        .padding(.vertical, 100)
    }
}

// MARK: - Filter Chip

struct FilterChip: View {
    let title: String
    var isLocalizedKey: Bool = false
    var color: Color? = nil
    let isSelected: Bool
    let action: () -> Void
    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        Button(action: action) {
            Group {
                if isLocalizedKey {
                    Text(LocalizedStringKey(title))
                } else {
                    Text(title)
                }
            }
            .font(.system(size: 15, weight: .bold))
            .padding(.horizontal, 22)
            .padding(.vertical, 10)
            .foregroundStyle(isSelected ? (colorScheme == .dark ? .white : (color ?? Color.Alpha.brand)) : Color.Alpha.textSecondary)
            .background(
                Capsule()
                    .fill(isSelected 
                          ? (colorScheme == .dark ? Color.Alpha.brand.opacity(0.3) : (color?.opacity(0.08) ?? Color.Alpha.brand.opacity(0.08))) 
                          : (colorScheme == .dark ? Color.Alpha.surface : Color.Alpha.surfaceContainerLow))
            )
            .overlay(
                Capsule()
                    .stroke((color ?? Color.Alpha.brand).opacity(isSelected ? 0.2 : 0), lineWidth: 1)
            )
        }
    }
}

// MARK: - Group Manager

struct GroupManagerView: View {
    let groups: [WatchlistGroup]
    let selectedGroupId: String?
    let mode: GroupManagerMode
    let onSelect: (String?) -> Void
    let onDeleteGroup: (String) -> Void
    let onMoveGroup: ((IndexSet, Int) -> Void)?
    
    @Environment(\.dismiss) var dismiss
    @State private var pendingDeleteGroup: WatchlistGroup?
    @State private var showDeleteConfirmation = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                List {
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
                                    pendingDeleteGroup = group
                                    showDeleteConfirmation = true
                                } label: {
                                    Label("funds.action.delete", systemImage: "trash")
                                }
                            }
                        }
                        .onMove { indices, newOffset in
                            onMoveGroup?(indices, newOffset)
                        }
                    }
                    
                    if mode == .moveFund {
                        Section {
                            Button {
                                onSelect(nil)
                                dismiss()
                            } label: {
                                HStack {
                                    Text("funds.group.all")
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
            .navigationTitle(mode == .filter ? Text(LocalizedStringKey("funds.group.manage_title")) : Text(LocalizedStringKey("funds.group.move_title")))
            .navigationBarTitleDisplayMode(.inline)
            .alert(
                Text(LocalizedStringKey("funds.action.delete")),
                isPresented: $showDeleteConfirmation,
                presenting: pendingDeleteGroup
            ) { group in
                Button("funds.action.cancel", role: .cancel) { }
                Button("funds.action.delete", role: .destructive) {
                    onDeleteGroup(group.id)
                    pendingDeleteGroup = nil
                }
            } message: { group in
                Text(group.name)
            }
            .toolbar {
                if mode == .filter {
                    ToolbarItem(placement: .topBarTrailing) {
                        EditButton()
                    }
                }
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

// MARK: - Create Group Form

struct CreateGroupForm: View {
    @State private var groupName = ""
    @FocusState private var isGroupNameFocused: Bool
    @Environment(\.dismiss) var dismiss

    let onCreate: (String, String, String) -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("funds.group.name_placeholder", text: $groupName)
                        .autocapitalization(.none)
                        .focused($isGroupNameFocused)
                } header: {
                    Text(LocalizedStringKey("funds.group.name"))
                }
            }
            .navigationTitle("funds.group.new")
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
