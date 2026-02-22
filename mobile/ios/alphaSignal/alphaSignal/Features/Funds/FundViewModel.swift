import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI
import SwiftData

// MARK: - 排序模式

enum FundSortOrder: CaseIterable {
    case none           // 自定义排序
    case highGrowthFirst  // 涨幅榜
    case highDropFirst    // 跌幅榜
    case alphabetical     // 名称 A-Z
    
    var icon: String {
        switch self {
        case .none: return "line.3.horizontal.decrease.circle"
        case .highGrowthFirst: return "arrow.up.circle.fill"
        case .highDropFirst: return "arrow.down.circle.fill"
        case .alphabetical: return "textformat"
        }
    }
    
    var label: String {
        switch self {
        case .none: return "自定义"
        case .highGrowthFirst: return "涨幅榜"
        case .highDropFirst: return "跌幅榜"
        case .alphabetical: return "名称"
        }
    }
}

// MARK: - 视图模式

enum WatchlistViewMode {
    case all
    case group(String)
}

// MARK: - ViewModel

@Observable
@MainActor
class FundViewModel {
    // MARK: - Published Properties
    
    var watchlist: [FundValuation] = []
    var watchlistItems: [WatchlistItem] = []
    var groups: [WatchlistGroup] = []
    var sortOrder: FundSortOrder = .none
    var viewMode: WatchlistViewMode = .all
    var selectedGroupId: String? = nil
    
    var isLoading = false
    var isSyncing = false
    var isLoadingValuations = false
    
    var syncError: Error?
    var lastSyncTime: Date?
    
    // 编辑模式
    var isEditing = false
    var selectedFundCodes: Set<String> = []
    
    // 删除确认
    var pendingDeleteFund: FundValuation?
    var lastDeletedFund: DeletedFundInfo?
    
    // 分组操作
    var pendingMoveFund: FundValuation?
    var showGroupPicker = false
    
    // 搜索添加
    var showAddFundSheet = false
    
    // MARK: - Private Properties
    
    private let syncEngine = WatchlistSyncEngine.shared
    private let cacheManager = WatchlistCacheManager.shared
    private var modelContext: ModelContext?

    // MARK: - Derived Data

    var sortedWatchlist: [FundValuation] {
        guard !watchlist.isEmpty else { return [] }

        let itemsByCode = Dictionary(uniqueKeysWithValues: watchlistItems.map { ($0.fundCode, $0) })
        let baseIndex = Dictionary(uniqueKeysWithValues: watchlist.enumerated().map { ($0.element.fundCode, $0.offset) })

        let filtered = watchlist.filter { valuation in
            switch viewMode {
            case .all:
                return true
            case .group(let groupId):
                return itemsByCode[valuation.fundCode]?.groupId == groupId
            }
        }

        func sortIndex(for valuation: FundValuation) -> Int {
            if let item = itemsByCode[valuation.fundCode] {
                return item.sortIndex
            }
            return baseIndex[valuation.fundCode] ?? 0
        }

        switch sortOrder {
        case .none:
            return filtered.sorted { sortIndex(for: $0) < sortIndex(for: $1) }
        case .alphabetical:
            return filtered.sorted {
                let cmp = $0.fundName.localizedStandardCompare($1.fundName)
                if cmp == .orderedSame {
                    return sortIndex(for: $0) < sortIndex(for: $1)
                }
                return cmp == .orderedAscending
            }
        case .highGrowthFirst:
            return filtered.sorted {
                if $0.estimatedGrowth == $1.estimatedGrowth {
                    return sortIndex(for: $0) < sortIndex(for: $1)
                }
                return $0.estimatedGrowth > $1.estimatedGrowth
            }
        case .highDropFirst:
            return filtered.sorted {
                if $0.estimatedGrowth == $1.estimatedGrowth {
                    return sortIndex(for: $0) < sortIndex(for: $1)
                }
                return $0.estimatedGrowth < $1.estimatedGrowth
            }
        }
    }
    
    // MARK: - Initialization
    
    init() {
        setupNotifications()
        Task {
            await setupSyncEngine()
        }
    }
    
    private func setupNotifications() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleSyncNotification(_:)),
            name: NSNotification.Name("WatchlistDidSync"),
            object: nil
        )
    }
    
    @objc private func handleSyncNotification(_ notification: Notification) {
        Task {
            await fetchWatchlist()
        }
    }
    
    // MARK: - Setup
    
    func setModelContext(_ context: ModelContext) {
        self.modelContext = context
        Task {
            await cacheManager.setup(modelContext: context)
        }
    }
    
    private func setupSyncEngine() async {
        await syncEngine.setup(lastSyncTime: lastSyncTime)
    }
    
    // MARK: - Helper Methods for API Calls
    
    private func sendRequest<T: Encodable, U: Decodable>(
        path: String,
        method: String,
        body: T
    ) async throws -> U {
        return try await APIClient.shared.send(
            path: path,
            method: method,
            body: body
        )
    }
    
    // MARK: - Fetch Data
    
    func fetchWatchlist() async {
        isLoading = true
        
        do {
            // 1. 获取自选列表（含分组）
            let response: WatchlistItemsResponse = try await APIClient.shared.fetch(
                path: "/api/v2/watchlist"
            )
            
            // 2. 更新本地缓存
            await cacheManager.saveGroups(response.groups)
            await cacheManager.saveItems(response.data)
            
            // 3. 更新本地数据
            self.groups = response.groups
            self.watchlistItems = response.data
            
            // 4. 获取估值数据
            let codes = response.data.map { $0.fundCode }
            if !codes.isEmpty {
                await fetchValuations(for: codes)
            } else {
                self.watchlist = []
            }
            
            syncError = nil
            
        } catch {
            syncError = error
            print("❌ Failed to fetch watchlist: \(error)")
            
            // 降级：从缓存读取
            await loadFromCache()
        }
        
        isLoading = false
    }
    
    func fetchGroups() async {
        do {
            let response: WatchlistGroupsResponse = try await APIClient.shared.fetch(
                path: "/api/v2/watchlist/groups"
            )
            self.groups = response.data
            
            // 更新缓存
            await cacheManager.saveGroups(response.data)
        } catch {
            print("❌ Failed to fetch groups: \(error)")
        }
    }
    
    private func fetchValuations(for codes: [String]) async {
        isLoadingValuations = true
        
        do {
            let codesParam = codes.joined(separator: ",")
            let response: BatchValuationResponse = try await APIClient.shared.fetch(
                path: "/api/v1/web/funds/batch-valuation?codes=\(codesParam)&mode=summary"
            )
            
            withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                self.watchlist = response.data
            }
        } catch {
            print("❌ Failed to fetch valuations: \(error)")
        }
        
        isLoadingValuations = false
    }
    
    private func loadFromCache() async {
        let cachedItems = await cacheManager.fetchAllItems()
        self.watchlistItems = cachedItems.map {
            WatchlistItem(
                id: UUID().uuidString,
                userId: "",
                fundCode: $0.fundCode,
                fundName: $0.fundName,
                groupId: $0.groupId,
                sortIndex: Int($0.sortIndex),
                createdAt: $0.lastSyncTime,
                updatedAt: $0.lastSyncTime,
                isDeleted: $0.isDeleted
            )
        }
        let codes = cachedItems.map { $0.fundCode }
        
        if !codes.isEmpty {
            await fetchValuations(for: codes)
        }
    }
    
    // MARK: - Add Fund
    
    func addFund(code: String, name: String, groupId: String? = nil) async {
        // 1. 检查是否已存在
        if watchlist.contains(where: { $0.fundCode == code }) {
            print("⚠️ Fund already in watchlist: \(code)")
            return
        }
        
        // 2. 乐观更新 UI
        let tempValuation = FundValuation(
            fundCode: code,
            fundName: name,
            estimatedGrowth: 0,
            totalWeight: 0,
            components: [],
            timestamp: Date()
        )
        
        withAnimation(.spring()) {
            watchlist.append(tempValuation)
        }
        
        // 3. 加入待同步队列
        await syncEngine.enqueueAdd(fundCode: code, fundName: name, groupId: groupId)
        
        // 4. 保存到缓存
        let item = WatchlistItem(
            id: UUID().uuidString,
            userId: "",
            fundCode: code,
            fundName: name,
            groupId: groupId,
            sortIndex: watchlist.count - 1,
            createdAt: Date(),
            updatedAt: Date(),
            isDeleted: false
        )
        await cacheManager.saveItem(item)
        
        // 5. 调用 API
        do {
            let request = WatchlistBatchAddRequest(items: [
                WatchlistBatchItem(code: code, name: name, groupId: groupId)
            ])

            // 使用辅助函数来避免泛型推断问题
            try await sendBatchAddRequest(request)

            // 6. 刷新列表
            await fetchWatchlist()

        } catch {
            print("❌ Failed to add fund: \(error)")
            // 不回滚，依赖同步机制
        }
    }
    
    // MARK: - API Helper Methods
    
    private func sendBatchAddRequest(_ request: WatchlistBatchAddRequest) async throws {
        let _: SuccessResponse = try await APIClient.shared.send(path: "/api/v2/watchlist/batch-add", method: "POST", body: request)
    }
    
    // MARK: - Delete Fund
    
    func deleteFund(code: String) async {
        // 1. 找到要删除的基金
        guard let fund = watchlist.first(where: { $0.fundCode == code }) else { return }
        
        // 2. 保存删除信息（用于撤销）
        lastDeletedFund = DeletedFundInfo(
            fund: fund,
            index: watchlist.firstIndex(where: { $0.fundCode == code }) ?? 0
        )
        
        // 3. 乐观删除 UI
        withAnimation(.spring()) {
            watchlist.removeAll { $0.fundCode == code }
        }
        
        // 4. 加入待同步队列
        await syncEngine.enqueueRemove(fundCode: code)
        
        // 5. 调用 API
        do {
            let _: SuccessResponse = try await APIClient.shared.fetch(
                path: "/api/v1/web/watchlist/\(code)",
                method: "DELETE"
            )
            
            // 6. 从缓存删除
            await cacheManager.deleteItem(fundCode: code)
            
            // 7. 清除删除信息（5 秒后自动清除）
            DispatchQueue.main.asyncAfter(deadline: .now() + 5) { [weak self] in
                self?.lastDeletedFund = nil
            }
            
        } catch {
            print("❌ Failed to delete fund: \(error)")
            // 回滚 UI
            withAnimation {
                watchlist.insert(fund, at: lastDeletedFund?.index ?? 0)
            }
            lastDeletedFund = nil
        }
    }
    
    func undoDelete() async {
        guard let info = lastDeletedFund else { return }
        
        // 恢复 UI
        withAnimation(.spring()) {
            watchlist.insert(info.fund, at: info.index)
        }
        
        // 取消删除操作（重新添加）
        await syncEngine.enqueueAdd(
            fundCode: info.fund.fundCode,
            fundName: info.fund.fundName
        )
        
        lastDeletedFund = nil
        
        // 刷新列表
        await fetchWatchlist()
    }
    
    // MARK: - Batch Delete
    
    func batchDelete() async {
        guard !selectedFundCodes.isEmpty else { return }
        
        let codesToDelete = Array(selectedFundCodes)
        
        // 乐观删除 UI
        withAnimation(.spring()) {
            watchlist.removeAll { selectedFundCodes.contains($0.fundCode) }
        }
        
        // 加入待同步队列
        for code in codesToDelete {
            await syncEngine.enqueueRemove(fundCode: code)
        }
        
        // 调用 API
        do {
            let request = WatchlistBatchRemoveRequest(codes: codesToDelete)
            try await sendBatchRemoveRequest(request)

            // 清空选择
            selectedFundCodes.removeAll()
            isEditing = false

        } catch {
            print("❌ Failed to batch delete: \(error)")
            await fetchWatchlist()
        }
    }
    
    private func sendBatchRemoveRequest(_ request: WatchlistBatchRemoveRequest) async throws {
        let _: SuccessResponse = try await APIClient.shared.send(path: "/api/v2/watchlist/batch-remove", method: "POST", body: request)
    }
    
    // MARK: - Move Group
    
    func moveFundToGroup(code: String, groupId: String?) async {
        guard watchlist.contains(where: { $0.fundCode == code }) else { return }
        
        // 乐观更新
        // TODO: 更新本地 groupId
        
        // 加入待同步队列
        await syncEngine.enqueueMove(fundCode: code, groupId: groupId)
        
        // 调用 API
        do {
            let request = WatchlistMoveGroupRequest(groupId: groupId)
            try await sendMoveGroupRequest(code, request)

            await fetchWatchlist()

        } catch {
            print("❌ Failed to move fund to group: \(error)")
            await fetchWatchlist()
        }
    }
    
    private func sendMoveGroupRequest(_ code: String, _ request: WatchlistMoveGroupRequest) async throws {
        let _: SuccessResponse = try await APIClient.shared.send(path: "/api/v2/watchlist/\(code)/group", method: "PUT", body: request)
    }
    
    // MARK: - Reorder
    
    func reorder(from offsets: IndexSet, to newOffset: Int) {
        guard sortOrder == .none else { return } // 只在自定义排序模式下允许拖拽
        
        // TODO: 实现拖拽排序逻辑
        // watchlist.move(fromOffsets: offsets, toOffset: newOffset)
        
        // 加入待同步队列
        Task {
            for index in offsets {
                await syncEngine.enqueueReorder(
                    fundCode: watchlist[index].fundCode,
                    sortIndex: newOffset
                )
            }
        }
    }
    
    // MARK: - Toggle Selection
    
    func toggleSelection(_ code: String) {
        if selectedFundCodes.contains(code) {
            selectedFundCodes.remove(code)
        } else {
            selectedFundCodes.insert(code)
        }
    }
    
    func toggleSortOrder() {
        if let currentIndex = FundSortOrder.allCases.firstIndex(of: sortOrder) {
            let nextIndex = (currentIndex + 1) % FundSortOrder.allCases.count
            sortOrder = FundSortOrder.allCases[nextIndex]
        }
    }
    
    // MARK: - Create Group
    
    func createGroup(name: String, icon: String, color: String) async {
        do {
            let request = WatchlistCreateGroupRequest(name: name, icon: icon, color: color)
            let response: WatchlistGroupsResponse = try await APIClient.shared.send(
                path: "/api/v2/watchlist/groups",
                method: "POST",
                body: request
            )
            
            groups.append(response.data.first!)
            await cacheManager.saveGroup(response.data.first!)
            
        } catch {
            print("❌ Failed to create group: \(error)")
        }
    }
    
    // MARK: - Delete Group
    
    func deleteGroup(groupId: String) async {
        do {
            let _: SuccessResponse = try await APIClient.shared.fetch(
                path: "/api/v2/watchlist/groups/\(groupId)",
                method: "DELETE"
            )
            
            withAnimation {
                groups.removeAll { $0.id == groupId }
            }
            
            await cacheManager.deleteGroup(id: groupId)
            
            // 如果当前选中的是该分组，切换回全部
            if case .group(let selectedId) = viewMode, selectedId == groupId {
                viewMode = .all
            }
            
        } catch {
            print("❌ Failed to delete group: \(error)")
        }
    }
    
    // MARK: - Live Updates
    
    func startLiveUpdates() {
        // TODO: 启动实时估值更新
    }
    
    func stopLiveUpdates() {
        // TODO: 停止实时估值更新
    }
}

// MARK: - Helper Types

struct DeletedFundInfo {
    let fund: FundValuation
    let index: Int
}

// MARK: - DTOs (保留向后兼容)

struct WatchlistDataResponse: Codable {
    let data: [WatchlistItemDTO]
}

struct WatchlistItemDTO: Codable {
    let code: String
    let name: String
}

struct BatchValuationResponse: Codable {
    let data: [FundValuation]
}

struct SuccessResponse: Codable {
    let success: Bool
}
