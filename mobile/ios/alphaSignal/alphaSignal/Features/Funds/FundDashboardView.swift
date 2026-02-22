import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore
import SwiftData

struct FundDashboardView: View {
    @State private var viewModel = FundViewModel()
    @Environment(\.colorScheme) var colorScheme
    @Environment(\.modelContext) private var modelContext
    
    @State private var showAddFundSheet = false
    @State private var showGroupPicker = false
    @State private var pendingMoveFund: FundValuation?
    @State private var showDeleteConfirmation = false
    @State private var pendingDeleteFund: FundValuation?
    @State private var showBatchDeleteConfirmation = false
    @State private var showCreateGroupSheet = false
    @State private var selectedGroupForFilter: String? = nil
    
    var body: some View {
        NavigationStack {
            dashboardContent
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { dashboardToolbar }
        }
        .modelContext(modelContext)
        .task {
            viewModel.setModelContext(modelContext)
            await viewModel.fetchWatchlist()
            await viewModel.fetchGroups()
        }
        .sheet(isPresented: $showAddFundSheet) {
            FundSearchView { fund in
                Task {
                    await viewModel.addFund(code: fund.code, name: fund.name)
                }
            }
            .presentationDetents([.medium, .large])
            .presentationDragIndicator(.visible)
        }
        .sheet(isPresented: $showCreateGroupSheet) {
            CreateGroupView { name, icon, color in
                Task {
                    await viewModel.createGroup(name: name, icon: icon, color: color)
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
        .alert("批量删除", isPresented: $showBatchDeleteConfirmation) {
            Button("取消", role: .cancel) { }
            Button("删除 (\(viewModel.selectedFundCodes.count))", role: .destructive) {
                Task {
                    await viewModel.batchDelete()
                }
            }
        } message: {
            Text("确定要删除选中的 \(viewModel.selectedFundCodes.count) 只基金吗？此操作不可撤销。")
        }
    }

    // MARK: - Subviews

    private var dashboardContent: some View {
        ZStack {
            LiquidBackground()
            VStack(spacing: 0) {
                headerSection
                listSection
            }
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

            filterChips
        }
        .padding(.horizontal)
        .padding(.top, 24)
        .padding(.bottom, 12)
    }

    @ViewBuilder
    private var filterChips: some View {
        if !viewModel.groups.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
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
    }

    private var listSection: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: 16) {
                if viewModel.watchlist.isEmpty && !viewModel.isLoading {
                    emptyStateView
                } else {
                    if viewModel.isEditing {
                        editModeToolbar
                    }

                    if viewModel.isEditing {
                        editModeListView
                    } else {
                        normalListView
                    }
                }

                Spacer(minLength: 100)
            }
            .padding(.top, 12)
        }
    }

    @ToolbarContentBuilder
    private var dashboardToolbar: some ToolbarContent {
        if !viewModel.watchlist.isEmpty {
            ToolbarItem(placement: .topBarLeading) {
                Button(viewModel.isEditing ? "取消" : "编辑") {
                    withAnimation(.spring()) {
                        viewModel.isEditing.toggle()
                        if !viewModel.isEditing {
                            viewModel.selectedFundCodes.removeAll()
                        }
                    }
                }
            }
        }

        ToolbarItem {
            Menu {
                ForEach(FundSortOrder.allCases, id: \.self) { order in
                    Button {
                        withAnimation(.spring()) {
                            viewModel.sortOrder = order
                        }
                    } label: {
                        HStack {
                            Image(systemName: order.icon)
                            Text(order.label)
                            if viewModel.sortOrder == order {
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                }
            } label: {
                Image(systemName: viewModel.sortOrder.icon)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(.blue)
            }
        }

        ToolbarSpacer(.fixed)

        ToolbarItem(placement: .topBarTrailing) {
            Button {
                showAddFundSheet = true
            } label: {
                Image(systemName: "plus.circle.fill")
                    .font(.system(size: 20))
                    .foregroundStyle(.blue)
            }
        }

        ToolbarItem(placement: .topBarTrailing) {
            Button {
                Task { await viewModel.fetchWatchlist() }
            } label: {
                Image(systemName: "arrow.clockwise")
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
                
                Button {
                    showAddFundSheet = true
                } label: {
                    HStack {
                        Image(systemName: "plus.circle.fill")
                        Text("添加第一只基金")
                    }
                    .padding()
                    .background(.blue)
                    .foregroundStyle(.white)
                    .cornerRadius(12)
                }
                
                Spacer()
            }
        }
    }
    
    // MARK: - Edit Mode
    
    private var editModeToolbar: some View {
        HStack {
            Text("已选择 \(viewModel.selectedFundCodes.count) 只基金")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            
            Spacer()
            
            Button("删除") {
                showBatchDeleteConfirmation = true
            }
            .font(.subheadline.bold())
            .foregroundStyle(.red)
            .disabled(viewModel.selectedFundCodes.isEmpty)
        }
        .padding(.horizontal)
        .padding(.bottom, 8)
    }
    
    private var editModeListView: some View {
        VStack(spacing: 12) {
            ForEach(viewModel.sortedWatchlist) { valuation in
                let isSelected = viewModel.selectedFundCodes.contains(valuation.fundCode)
                HStack {
                    Button {
                        viewModel.toggleSelection(valuation.fundCode)
                    } label: {
                        Image(systemName: isSelected
                              ? "checkmark.circle.fill"
                              : "circle")
                        .font(.system(size: 22))
                        .foregroundStyle(isSelected
                                         ? .blue
                                         : .gray)
                    }
                    
                    FundCompactCard(valuation: valuation)
                        .opacity(isSelected ? 0.5 : 1)
                }
            }
        }
        .padding(.horizontal)
    }
    
    private var normalListView: some View {
        VStack(spacing: 16) {
            ForEach(viewModel.sortedWatchlist) { valuation in
                NavigationLink(destination: FundDetailView(valuation: valuation)) {
                    FundCompactCard(valuation: valuation)
                }
                .buttonStyle(.plain)
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
                .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                    Button(role: .destructive) {
                        pendingDeleteFund = valuation
                        showDeleteConfirmation = true
                    } label: {
                        Label("删除", systemImage: "trash")
                    }
                    
                    Button {
                        pendingMoveFund = valuation
                        showGroupPicker = true
                    } label: {
                        Label("移动", systemImage: "folder.badge.plus")
                    }
                    .tint(.orange)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal)
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
            .background(
                RoundedRectangle(cornerRadius: 20)
                    .fill(isSelected ? (color ?? .blue) : .white.opacity(0.5))
            )
            .foregroundStyle(isSelected ? .white : .primary)
            .overlay(
                RoundedRectangle(cornerRadius: 20)
                    .strokeBorder(isSelected ? Color.clear : Color.gray.opacity(0.3), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
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
