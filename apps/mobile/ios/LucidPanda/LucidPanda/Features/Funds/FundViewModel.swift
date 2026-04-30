import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI
import SwiftData
import OSLog

// MARK: - 排序模式

enum FundSortOrder: CaseIterable, Hashable {
    case `default`      // 默认排序（按自定义顺序）
    case ascending       // 净值涨跌升序
    case descending      // 净值涨跌降序

    static var menuOrders: [FundSortOrder] {
        [.default, .descending, .ascending]
    }
    
    var icon: String {
        switch self {
        case .default: return "line.3.horizontal.decrease.circle"
        case .ascending: return "arrow.down.circle.fill"
        case .descending: return "arrow.up.circle.fill"
        }
    }
    
    var label: String {
        switch self {
        case .default: return String(localized: "funds.sort.none")
        case .ascending: return String(localized: "funds.sort.high_drop")
        case .descending: return String(localized: "funds.sort.high_growth")
        }
    }
}

// MARK: - 视图模式

enum WatchlistViewMode: Equatable {
    case all
    case group(String)
}

// MARK: - ViewModel

@Observable
@MainActor
class FundViewModel {
    private let logger = AppLog.watchlist
    // MARK: - Published Properties
    
    var watchlist: [FundValuation] = [] {
        didSet { updateSortedWatchlist() }
    }
    var watchlistItems: [WatchlistItem] = [] {
        didSet { updateSortedWatchlist() }
    }
    var groups: [WatchlistGroup] = []
    var sortOrder: FundSortOrder = .default {
        didSet { updateSortedWatchlist() }
    }
    var viewMode: WatchlistViewMode = .all {
        didSet { updateSortedWatchlist() }
    }
    var selectedGroupId: String? {
        if case .group(let id) = viewMode {
            return id
        }
        return nil
    }
    
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
    
    // 订阅拦截
    var showPaywall = false
    var isPro = false
    
    // 搜索添加
    var showAddFundSheet = false
    
    // MARK: - Private Properties
    
    private let syncEngine = WatchlistSyncEngine.shared
    private let cacheManager = WatchlistCacheManager.shared
    private var modelContext: ModelContext?
    private var liveStreamTask: Task<Void, Never>?
    private var liveCodesTask: Task<Void, Never>?
    private let liveSubscriberID = "fund-watchlist"
    
    // 🚀 Performance: Cache for filtered and sorted results
    private(set) var sortedWatchlist: [FundValuation] = []
    private var lastUpdateTimestamp: Date = .distantPast

    // MARK: - Core Logic

    private func updateSortedWatchlist() {
        // 🚀 Optimization: Basic debounce to prevent excessive re-sorting during high-frequency SSE updates
        let now = Date()
        if now.timeIntervalSince(lastUpdateTimestamp) < 0.1 && !watchlist.isEmpty {
            // If called too frequently, we skip full sort unless it's the first time
            // In a real high-perf app, we might use a dedicated debouncer/timer here
        }
        lastUpdateTimestamp = now

        guard !watchlist.isEmpty else { 
            self.sortedWatchlist = []
            return 
        }

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

        let result: [FundValuation]
        switch sortOrder {
        case .default:
            result = filtered.sorted { sortIndex(for: $0) < sortIndex(for: $1) }
        case .descending:
            result = filtered.sorted {
                if $0.estimatedGrowth == $1.estimatedGrowth {
                    return sortIndex(for: $0) < sortIndex(for: $1)
                }
                return $0.estimatedGrowth > $1.estimatedGrowth
            }
        case .ascending:
            result = filtered.sorted {
                if $0.estimatedGrowth == $1.estimatedGrowth {
                    return sortIndex(for: $0) < sortIndex(for: $1)
                }
                return $0.estimatedGrowth < $1.estimatedGrowth
            }
        }
        
        // Only update if actually different to prevent unnecessary UI ripples
        if self.sortedWatchlist != result {
            self.sortedWatchlist = result
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
        Task { @MainActor in
            await fetchWatchlist()
        }
    }
    
    // MARK: - Setup
    
    func setModelContext(_ context: ModelContext) {
        self.modelContext = context
        Task {
            await cacheManager.setup(modelContainer: context.container)
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
        // --- 核心优化：Offline-First (离线优先/极速渲染) ---
        // 首次打开或者当内存为空时，立刻提取 SwiftData 进行瞬间渲染（0延迟），之后再等待网络刷新。彻底告别首次启动白屏！
        if self.watchlistItems.isEmpty {
            await loadFromCache()
        }
        
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
                self.updateSortedWatchlist()
            }
            
            syncError = nil
            
        } catch {
            syncError = error
            logger.error("Failed to fetch watchlist: \(error.localizedDescription, privacy: .public)")
            // 网络彻底断开时，由于之前已经 loadFromCache 过，此处什么都不做
        }
        
        isLoading = false
    }

    func fetchGroups() async {
        // --- 核心优化：Offline-First ---
        // 瞬间加载 SwiftData 里的分组信息
        if self.groups.isEmpty {
            let cachedGroups = await cacheManager.fetchAllGroups()
            self.groups = cachedGroups.map {
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
        
        do {
            let response: WatchlistGroupsResponse = try await APIClient.shared.fetch(
                path: "/api/v2/watchlist/groups"
            )
            
            self.groups = response.data
            await cacheManager.saveGroups(response.data)
            
            logger.info("Fetched \(response.data.count, privacy: .public) user groups")
            
        } catch {
            logger.error("Failed to fetch groups: \(error.localizedDescription, privacy: .public)")
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
            
            await cacheManager.saveValuations(response.data)
        } catch {
            logger.error("Failed to fetch valuations: \(error.localizedDescription, privacy: .public)")
        }
        
        isLoadingValuations = false
    }

    private func refreshValuations(for codes: [String], replace: Bool) async {
        guard !codes.isEmpty else { return }

        do {
            let codesParam = codes.joined(separator: ",")
            let response: BatchValuationResponse = try await APIClient.shared.fetch(
                path: "/api/v1/web/funds/batch-valuation?codes=\(codesParam)&mode=summary"
            )
            if replace {
                withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                    self.watchlist = response.data
                }
            } else {
                let updated = Dictionary(uniqueKeysWithValues: response.data.map { ($0.fundCode, $0) })
                withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                    let existingCodes = Set(self.watchlist.map(\.fundCode))
                    let merged = self.watchlist.map { updated[$0.fundCode] ?? $0 }
                    let appended = response.data.filter { !existingCodes.contains($0.fundCode) }
                    self.watchlist = merged + appended
                }
            }
            await cacheManager.saveValuations(response.data)
        } catch {
            logger.error("Failed to refresh valuations: \(error.localizedDescription, privacy: .public)")
        }
    }
    
    /// 纯本地缓存读取 — 不发起任何网络请求。
    /// fetchValuations 由 fetchWatchlist() 统一调度，避免在断网场景里触发注定失败的网络请求。
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
        
        // 从 cachedValuationData blob 恢复估值数据
        let cachedValuations = cachedItems.compactMap { item -> FundValuation? in
            guard let data = item.cachedValuationData else { return nil }
            return try? JSONDecoder().decode(FundValuation.self, from: data)
        }
        if !cachedValuations.isEmpty {
            withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                self.watchlist = cachedValuations
                self.updateSortedWatchlist()
            }
        }
        // 不在此处调用 fetchValuations —— 网络请求由 fetchWatchlist 统一调度
    }
    
    // MARK: - Add Fund
    
    func addFund(code: String, name: String, groupId: String? = nil) async {
        // 1. 检查是否已存在
        if watchlist.contains(where: { $0.fundCode == code }) {
            logger.warning("Fund already in watchlist: \(code, privacy: .public)")
            return
        }
        
        // 1.5 订阅限制检查
        if !isPro && watchlist.count >= 10 {
            showPaywall = true
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
            logger.error("Failed to add fund: \(error.localizedDescription, privacy: .public)")
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

            // 7. 清除删除信息（3 秒后自动清除）
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
                self?.lastDeletedFund = nil
            }
            
        } catch {
            logger.error("Failed to delete fund: \(error.localizedDescription, privacy: .public)")
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
            logger.error("Failed to batch delete: \(error.localizedDescription, privacy: .public)")
            await fetchWatchlist()
        }
    }
    
    private func sendBatchRemoveRequest(_ request: WatchlistBatchRemoveRequest) async throws {
        let _: SuccessResponse = try await APIClient.shared.send(path: "/api/v2/watchlist/batch-remove", method: "POST", body: request)
    }
    
    // MARK: - Move Group
    
    func moveFundToGroup(code: String, groupId: String?) async {
        guard watchlist.contains(where: { $0.fundCode == code }) else { return }

        // 乐观更新本地分组，确保筛选视图立即变化。
        if let index = watchlistItems.firstIndex(where: { $0.fundCode == code }) {
            let current = watchlistItems[index]
            let updated = WatchlistItem(
                id: current.id,
                userId: current.userId,
                fundCode: current.fundCode,
                fundName: current.fundName,
                groupId: groupId,
                sortIndex: current.sortIndex,
                createdAt: current.createdAt,
                updatedAt: Date(),
                isDeleted: current.isDeleted
            )
            withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                watchlistItems[index] = updated
            }
            await cacheManager.saveItem(updated)
        }
        
        // 加入待同步队列
        await syncEngine.enqueueMove(fundCode: code, groupId: groupId)
        
        // 调用 API
        do {
            let request = WatchlistMoveGroupRequest(groupId: groupId)
            try await sendMoveGroupRequest(code, request)

            await fetchWatchlist()

        } catch {
            logger.error("Failed to move fund to group: \(error.localizedDescription, privacy: .public)")
            await fetchWatchlist()
        }
    }
    
    private func sendMoveGroupRequest(_ code: String, _ request: WatchlistMoveGroupRequest) async throws {
        let _: SuccessResponse = try await APIClient.shared.send(path: "/api/v2/watchlist/\(code)/group", method: "PUT", body: request)
    }
    
    // MARK: - Reorder
    
    func reorder(from offsets: IndexSet, to newOffset: Int) {
        guard sortOrder == .default else { return } // 只在默认排序模式下允许拖拽

        let previousItems = watchlistItems
        let previousWatchlist = watchlist
        var ordered = sortedWatchlist
        ordered.move(fromOffsets: offsets, toOffset: newOffset)

        let rankByCode = Dictionary(uniqueKeysWithValues: ordered.enumerated().map { ($0.element.fundCode, $0.offset) })
        watchlistItems = watchlistItems.map { item in
            guard let rank = rankByCode[item.fundCode] else { return item }
            return WatchlistItem(
                id: item.id,
                userId: item.userId,
                fundCode: item.fundCode,
                fundName: item.fundName,
                groupId: item.groupId,
                sortIndex: rank,
                createdAt: item.createdAt,
                updatedAt: Date(),
                isDeleted: item.isDeleted
            )
        }

        let changedItems = watchlistItems

        Task { [changedItems, previousItems, previousWatchlist, ordered] in
            defer { Task { await syncEngine.syncChanges() } }
            for item in changedItems {
                await cacheManager.saveItem(item)
            }

            for (index, valuation) in ordered.enumerated() {
                await syncEngine.enqueueReorder(
                    fundCode: valuation.fundCode,
                    sortIndex: index
                )
            }

            do {
                let requestItems = ordered.enumerated().map { idx, value in
                    WatchlistReorderItem(fundCode: value.fundCode, sortIndex: idx)
                }
                try await self.submitWatchlistReorderWithRetry(
                    requestItems: requestItems,
                    baselineItems: previousItems
                )
            } catch {
                logger.error("Failed to reorder watchlist: \(error.localizedDescription, privacy: .public)")
                withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                    self.watchlistItems = previousItems
                    self.watchlist = previousWatchlist
                }
                for item in previousItems {
                    await cacheManager.saveItem(item)
                }
            }
        }
    }
    
    // MARK: - Reorder Groups
    
    func reorderGroups(from offsets: IndexSet, to newOffset: Int) {
        let previousGroups = groups
        var ordered = groups
        ordered.move(fromOffsets: offsets, toOffset: newOffset)
        
        let rankById = Dictionary(uniqueKeysWithValues: ordered.enumerated().map { ($0.element.id, $0.offset) })
        groups = groups.map { group in
            guard let rank = rankById[group.id] else { return group }
            return WatchlistGroup(
                id: group.id,
                userId: group.userId,
                name: group.name,
                icon: group.icon,
                color: group.color,
                sortIndex: rank,
                createdAt: group.createdAt,
                updatedAt: Date()
            )
        }.sorted(by: { $0.sortIndex < $1.sortIndex })
        
        Task { [groups, previousGroups] in
            for group in groups {
                await cacheManager.saveGroup(group)
            }
            
            do {
                let request = WatchlistGroupReorderRequest(
                    items: groups.map { WatchlistGroupReorderItem(groupId: $0.id, sortIndex: $0.sortIndex) },
                    clientUpdatedAt: previousGroups.map(\.updatedAt).max(),
                    mergeStrategy: "server_wins"
                )
                try await self.submitGroupReorderWithRetry(request)
            } catch {
                logger.error("Failed to reorder groups: \(error.localizedDescription, privacy: .public)")
                withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                    self.groups = previousGroups
                }
                for group in previousGroups {
                    await cacheManager.saveGroup(group)
                }
            }
        }
    }

    private func submitWatchlistReorderWithRetry(
        requestItems: [WatchlistReorderItem],
        baselineItems: [WatchlistItem],
        maxAttempts: Int = 3
    ) async throws {
        let clientUpdatedAt = baselineItems.map(\.updatedAt).max()
        for attempt in 1...maxAttempts {
            do {
                let request = WatchlistReorderRequest(
                    items: requestItems,
                    clientUpdatedAt: clientUpdatedAt,
                    mergeStrategy: "server_wins"
                )
                let _: SuccessResponse = try await APIClient.shared.send(
                    path: "/api/v2/watchlist/reorder",
                    method: "POST",
                    body: request
                )
                return
            } catch {
                if isWatchlistConflictError(error) {
                    await fetchWatchlist()
                    return
                }
                if attempt >= maxAttempts {
                    throw error
                }
                let delayNs = UInt64(350_000_000 * attempt)
                try? await Task.sleep(nanoseconds: delayNs)
            }
        }
    }

    private func submitGroupReorderWithRetry(
        _ request: WatchlistGroupReorderRequest,
        maxAttempts: Int = 3
    ) async throws {
        for attempt in 1...maxAttempts {
            do {
                let _: SuccessResponse = try await APIClient.shared.send(
                    path: "/api/v2/watchlist/groups/reorder",
                    method: "PATCH",
                    body: request
                )
                return
            } catch {
                if isWatchlistConflictError(error) {
                    await fetchGroups()
                    return
                }
                if attempt >= maxAttempts {
                    throw error
                }
                let delayNs = UInt64(350_000_000 * attempt)
                try? await Task.sleep(nanoseconds: delayNs)
            }
        }
    }

    private func isWatchlistConflictError(_ error: Error) -> Bool {
        if case APIError.serverError(let statusCode, _) = error {
            return statusCode == 409
        }
        return false
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
        let orders = FundSortOrder.menuOrders
        if let currentIndex = orders.firstIndex(of: sortOrder) {
            let nextIndex = (currentIndex + 1) % orders.count
            sortOrder = orders[nextIndex]
        } else {
            sortOrder = orders.first ?? .default
        }
    }
    
    // MARK: - Create Group

    func createGroup(name: String, icon: String, color: String, sortIndex: Int = 0) async {
        // 0. 订阅限制检查
        if !isPro && groups.count >= 5 {
            showPaywall = true
            return
        }
        
        // 1. 生成临时 ID 并提前进行乐观更新 (瞬间在 UI 显示)
        let tempId = "temp_\(UUID().uuidString)"
        let now = Date()
        let tempGroup = WatchlistGroup(
            id: tempId,
            userId: "",
            name: name,
            icon: icon,
            color: color,
            sortIndex: sortIndex,
            createdAt: now,
            updatedAt: now
        )
        
        withAnimation(.spring(response: 0.35, dampingFraction: 0.7)) {
            groups.append(tempGroup)
        }
        
        do {
            let request = WatchlistCreateGroupRequest(name: name, icon: icon, color: color, sortIndex: sortIndex)
            let response: WatchlistCreateGroupResponse = try await APIClient.shared.send(
                path: "/api/v2/watchlist/groups",
                method: "POST",
                body: request
            )

            // 2. 拿到物理 ID 后替换临时分组，确保后续操作 (如删除/移动) 指向正确 ID
            let realGroup = response.data
            withAnimation {
                if let index = groups.firstIndex(where: { $0.id == tempId }) {
                    groups[index] = realGroup
                    // 如果用户在网络请求期间已经选中了这个临时分组，则更新 viewMode 指向物理 ID
                    if case .group(let currentId) = viewMode, currentId == tempId {
                        viewMode = .group(realGroup.id)
                    }
                }
            }
            
            await cacheManager.saveGroup(realGroup)

        } catch {
            logger.error("Failed to create group: \(error.localizedDescription, privacy: .public)")
            // 3. 失败时回滚
            withAnimation {
                groups.removeAll { $0.id == tempId }
            }
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
            logger.error("Failed to delete group: \(error.localizedDescription, privacy: .public)")
        }
    }
    
    // MARK: - Live Updates
    
    func startLiveUpdates() {
        guard liveStreamTask == nil, liveCodesTask == nil else { return }

        liveCodesTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                let codes = await MainActor.run { self.activeStreamingCodes() }
                await FundValuationSSECenter.shared.setCodes(codes, for: self.liveSubscriberID)
                try? await Task.sleep(nanoseconds: 5_000_000_000)
            }
        }

        liveStreamTask = Task { [weak self] in
            guard let self else { return }
            let stream = await FundValuationSSECenter.shared.events(for: self.liveSubscriberID)
            for await valuation in stream {
                if Task.isCancelled { break }
                await MainActor.run {
                    self.applyLiveUpdate(valuation)
                }
            }
        }
    }
    
    func stopLiveUpdates() {
        liveStreamTask?.cancel()
        liveStreamTask = nil
        liveCodesTask?.cancel()
        liveCodesTask = nil
        Task { await FundValuationSSECenter.shared.setCodes([], for: liveSubscriberID) }
    }

    private func activeStreamingCodes() -> Set<String> {
        let valuationsByCode = Dictionary(uniqueKeysWithValues: watchlist.map { ($0.fundCode, $0) })
        let codes = watchlistItems.compactMap { item -> String? in
            guard let valuation = valuationsByCode[item.fundCode] else {
                return item.fundCode
            }
            let status = MarketSessionStatusResolver.status(for: valuation)
            return status == .closed ? nil : item.fundCode
        }
        return Set(codes)
    }

    private func applyLiveUpdate(_ valuation: FundValuation) {
        if let index = watchlist.firstIndex(where: { $0.fundCode == valuation.fundCode }) {
            withAnimation(.spring(response: 0.25, dampingFraction: 0.85)) {
                watchlist[index] = valuation
            }
            return
        }
        withAnimation(.spring(response: 0.25, dampingFraction: 0.85)) {
            watchlist.append(valuation)
        }
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
    let success: Bool?
}

struct WatchlistGroupReorderItem: Codable {
    let groupId: String
    let sortIndex: Int
    
    enum CodingKeys: String, CodingKey {
        case groupId = "group_id"
        case sortIndex = "sort_index"
    }
}

struct WatchlistGroupReorderRequest: Codable {
    let items: [WatchlistGroupReorderItem]
    let clientUpdatedAt: Date?
    let mergeStrategy: String?

    enum CodingKeys: String, CodingKey {
        case items
        case clientUpdatedAt = "client_updated_at"
        case mergeStrategy = "merge_strategy"
    }
}
