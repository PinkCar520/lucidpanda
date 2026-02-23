import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore
import SwiftData

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
        .sheet(isPresented: $showCreateGroupSheet) {
            CreateGroupView { name, icon, color in
                Task {
                    let sortIndex = viewModel.groups.count
                    await viewModel.createGroup(name: name, icon: icon, color: color, sortIndex: sortIndex)
                }
            }
        }
        .sheet(item: $pendingMoveFund) { fund in
            GroupPickerView(
                groups: viewModel.groups,
                selectedGroupId: nil
            ) { groupId in
                Task {
                    await viewModel.moveFundToGroup(code: fund.fundCode, groupId: groupId)
                }
            } onCreateGroup: {
                showCreateGroupSheet = true
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
        ZStack {
            LiquidBackground()
            listSection
        }
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("funds.title")
                        .font(.system(size: 24, weight: .black, design: .rounded))
                        .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                    Text("funds.subtitle")
                        .font(.caption2)
                        .foregroundStyle(.gray)
                }
                Spacer()
            }
        }
        .padding(.horizontal)
        .padding(.top, 24)
    }

    @ViewBuilder
    private var filterChips: some View {
        if !viewModel.groups.isEmpty {
            HStack(spacing: 8) {
                FilterChip(
                    title: "全部",
                    icon: "square.grid.2x2",
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
                        icon: group.icon,
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
    }

    private var listSection: some View {
        ScrollView(showsIndicators: false) {
            LazyVStack(spacing: 16, pinnedViews: [.sectionHeaders]) {
                headerSection
                    .padding(.top, 12)

                Section(header: filterChipsHeader) {
                    if viewModel.watchlist.isEmpty && !viewModel.isLoading {
                        emptyStateView
                            .padding(.horizontal)
                    } else {
                        ForEach(viewModel.sortedWatchlist) { valuation in
                            Button {
                                selectedFund = valuation
                                showFundDetail = true
                            } label: {
                                FundCompactCard(valuation: valuation)
                            }
                            .buttonStyle(.plain)
                            .contentShape(Rectangle())
                            .contextMenu {
                                Button {
                                    pendingMoveFund = valuation
                                    showGroupPicker = true
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
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    pendingDeleteFund = valuation
                                    showDeleteConfirmation = true
                                } label: {
                                    Label("删除", systemImage: "trash")
                                }
                            }
                            .padding(.horizontal)
                        }
                    }

                    Spacer(minLength: 100)
                }
            }
        }
        .refreshable {
            await viewModel.fetchWatchlist()
            await viewModel.fetchGroups()
        }
    }

    @ViewBuilder
    private var filterChipsHeader: some View {
        if !viewModel.groups.isEmpty {
            VStack(alignment: .leading, spacing: 0) {
                filterChips
            }
            .padding(.horizontal)
            .padding(.top, 8)
            .padding(.bottom, 12)
//            .background(Color(uiColor: .systemGroupedBackground))
        }
    }

    @ToolbarContentBuilder
    private var dashboardToolbar: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Button {
                showCreateGroupSheet = true
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
    let icon: String
    var color: Color? = nil
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 12, weight: .medium))
                Text(title)
                    .font(.subheadline.bold())
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .foregroundStyle(isSelected ? (color ?? .blue) : .primary)
        }
        .buttonStyle(.glass)
    }
}

// MARK: - Group Picker

struct GroupPickerView: View {
    let groups: [WatchlistGroup]
    let selectedGroupId: String?
    let onSelect: (String?) -> Void
    var onCreateGroup: () -> Void
    
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            List {
                Section {
                    Button {
                        onSelect(nil)
                        dismiss()
                    } label: {
                        HStack {
                            Image(systemName: "square.grid.2x2")
                            Text("无分组")
                            Spacer()
                            if selectedGroupId == nil {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(.blue)
                            }
                        }
                    }
                    
                    ForEach(groups) { group in
                        Button {
                            onSelect(group.id)
                            dismiss()
                        } label: {
                            HStack {
                                Image(systemName: group.icon)
                                    .foregroundStyle(Color(hex: group.color))
                                Text(group.name)
                                Spacer()
                                if selectedGroupId == group.id {
                                    Image(systemName: "checkmark")
                                        .foregroundStyle(.blue)
                                }
                            }
                        }
                    }
                }
                
                Section {
                    Button {
                        onCreateGroup()
                    } label: {
                        HStack {
                            Image(systemName: "plus.circle.fill")
                            Text("新建分组")
                        }
                        .foregroundStyle(.blue)
                    }
                }
            }
            .navigationTitle("选择分组")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("完成") {
                        dismiss()
                    }
                }
            }
        }
    }
}

// MARK: - Create Group View

struct CreateGroupView: View {
    @State private var groupName = ""
    @State private var selectedIcon = "folder"
    @State private var selectedColor = "#007AFF"
    @Environment(\.dismiss) var dismiss
    
    let onCreate: (String, String, String) -> Void
    
    private let icons = ["folder", "star", "heart", "bookmark", "flag", "globe", "chart.bar", "circle.grid.2x2"]
    private let colors = ["#007AFF", "#FF9500", "#FF2D55", "#5856D6", "#5AC8FA", "#4CD964", "#FFCC00", "#8E8E93"]
    
    var body: some View {
        NavigationStack {
            Form {
                Section("分组名称") {
                    TextField("如：科技基金、QDII", text: $groupName)
                }
                
                Section("图标") {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 12) {
                            ForEach(icons, id: \.self) { icon in
                                Button {
                                    selectedIcon = icon
                                } label: {
                                    Image(systemName: icon)
                                        .font(.system(size: 24))
                                        .frame(width: 44, height: 44)
                                        .background(
                                            Circle()
                                                .fill(selectedIcon == icon ? Color.blue.opacity(0.2) : Color.gray.opacity(0.1))
                                        )
                                        .foregroundStyle(selectedIcon == icon ? .blue : .primary)
                                }
                            }
                        }
                        .padding(.vertical, 8)
                    }
                }
                
                Section("颜色") {
                    HStack(spacing: 12) {
                        ForEach(colors, id: \.self) { color in
                            Button {
                                selectedColor = color
                            } label: {
                                Circle()
                                    .fill(Color(hex: color))
                                    .frame(width: 36, height: 36)
                                    .overlay(
                                        Circle()
                                            .stroke(Color.primary, lineWidth: selectedColor == color ? 3 : 0)
                                    )
                            }
                        }
                    }
                    .padding(.vertical, 8)
                }
            }
            .navigationTitle("新建分组")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("创建") {
                        onCreate(groupName, selectedIcon, selectedColor)
                        dismiss()
                    }
                    .disabled(groupName.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}
