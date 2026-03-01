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
    @State private var selectedFund: FundValuation?

    @State private var showFundDetail = false
    @State private var showGroupManager = false
    @State private var pendingMoveFundForManager: FundValuation?
    @State private var showCreateGroupOnly = false
    @State private var groupManagerMode: GroupManagerMode = .filter
    @State private var scrollOffset: CGFloat = 0

    var body: some View {
        @Bindable var viewModel = viewModel
        return NavigationStack {
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
                        ForEach(viewModel.sortedWatchlist) { valuation in
                            Button {
                                selectedFund = valuation
                                showFundDetail = true
                            } label: {
                                FundCompactCard(valuation: valuation)
                            }
                            .buttonStyle(LiquidScaleButtonStyle())
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
                            .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
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
            }
        }
    }

    @ViewBuilder
    private var filterChips: some View {
        if !viewModel.groups.isEmpty {
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

                    ForEach(viewModel.groups) { group in
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
                            .font(.system(size: 13, weight: .bold))
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

    var body: some View {
        Button(action: action) {
            Group {
                if isLocalizedKey {
                    Text(LocalizedStringKey(title))
                } else {
                    Text(title)
                }
            }
            .font(.system(size: 16, weight: .bold))
            .padding(.horizontal, 22)
            .padding(.vertical, 12)
            .foregroundStyle(isSelected ? (color ?? .blue) : .primary)
            .glassEffect(.regular, in: .capsule)
            .clipShape(Capsule())
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
    
    @Environment(\.dismiss) var dismiss
    
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
                                    onDeleteGroup(group.id)
                                } label: {
                                    Label("funds.action.delete", systemImage: "trash")
                                }
                            }
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
