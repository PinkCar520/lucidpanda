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
        ZStack(alignment: .top) {
            LiquidBackground()
            
            VStack(spacing: 0) {
                filterChipsHeader
                
                List {
                    if viewModel.watchlist.isEmpty && !viewModel.isLoading {
                        emptyStateView
                            .listRowInsets(EdgeInsets())
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                    } else {
                        ForEach(viewModel.sortedWatchlist) {
                            valuation in
                            Button {
                                selectedFund = valuation
                                    showFundDetail = true
                                } label: {
                                    FundCompactCard(valuation: valuation)
                                }
                            .buttonStyle(.plain)
                            .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    pendingDeleteFund = valuation
                                    showDeleteConfirmation = true
                                } label: {
                                    Label("删除", systemImage: "trash")
                                }
                                .tint(.red)
                                
                                Button {
                                    pendingMoveFundForManager = valuation
                                    groupManagerMode = .moveFund
                                    showGroupManager = true
                                } label: {
                                    Label("移动", systemImage: "folder.badge.plus")
                                }
                                .tint(.blue)
                            }
                        }
                        
                        Text("免责声明：系统估值基于公开持仓计算，仅供参考，不构成投资建议。\n市场有风险，投资需谨慎。")
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
            }
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
                .padding(.horizontal, 16)
            }
            .frame(height: 56) // 稍微变大以容纳更大的 Chip
        }
    }

    @ViewBuilder
    private var filterChipsHeader: some View {
        if !viewModel.groups.isEmpty {
            VStack(alignment: .leading, spacing: 0) {
                filterChips
                    .padding(.top, 4)
                    .padding(.bottom, 12)
                
                Divider()
                    .opacity(0.4)
            }
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
            Text("请使用底部搜索添加基金")
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


