// mobile/ios/alphaSignal/alphaSignal/Data/Cache/WatchlistCache.swift

import Foundation
import SwiftData
import AlphaData

// MARK: - 本地缓存模型

@Model
class LocalWatchlistItem {
    var fundCode: String
    var fundName: String
    var groupId: String?
    var sortIndex: Int32
    var lastSyncTime: Date
    var isDeleted: Bool
    var pendingOperationsData: Data?
    
    @Transient var pendingOperations: [PendingOperation] {
        get {
            guard let data = pendingOperationsData,
                  let ops = try? JSONDecoder().decode([PendingOperation].self, from: data) else {
                return []
            }
            return ops
        }
        set {
            pendingOperationsData = try? JSONEncoder().encode(newValue)
        }
    }
    
    init(fundCode: String, fundName: String, groupId: String? = nil, sortIndex: Int32 = 0) {
        self.fundCode = fundCode
        self.fundName = fundName
        self.groupId = groupId
        self.sortIndex = sortIndex
        self.lastSyncTime = Date()
        self.isDeleted = false
        self.pendingOperationsData = nil
    }
}

@Model
class LocalWatchlistGroup {
    var id: String
    var name: String
    var icon: String
    var color: String
    var sortIndex: Int32
    var lastSyncTime: Date
    
    init(id: String, name: String, icon: String, color: String, sortIndex: Int32) {
        self.id = id
        self.name = name
        self.icon = icon
        self.color = color
        self.sortIndex = sortIndex
        self.lastSyncTime = Date()
    }
}

// MARK: - 缓存管理器

actor WatchlistCacheManager {
    static let shared = WatchlistCacheManager()
    
    private var modelContext: ModelContext?
    private var isInitialized = false
    
    func setup(modelContext: ModelContext) {
        self.modelContext = modelContext
        self.isInitialized = true
    }
    
    // MARK: - 自选列表项操作
    
    func saveItem(_ item: WatchlistItem) async {
        guard let context = modelContext else { return }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistItem>(
                predicate: #Predicate { $0.fundCode == item.fundCode }
            )
            
            if let existing = try context.fetch(descriptor).first {
                // 更新现有项
                existing.fundName = item.fundName
                existing.groupId = item.groupId
                existing.sortIndex = Int32(item.sortIndex)
                existing.lastSyncTime = item.updatedAt
                existing.isDeleted = item.isDeleted
            } else {
                // 插入新项
                let localItem = LocalWatchlistItem(
                    fundCode: item.fundCode,
                    fundName: item.fundName,
                    groupId: item.groupId,
                    sortIndex: Int32(item.sortIndex)
                )
                context.insert(localItem)
            }
            
            try context.save()
        } catch {
            print("❌ Cache saveItem error: \(error)")
        }
    }
    
    func saveItems(_ items: [WatchlistItem]) async {
        for item in items {
            await saveItem(item)
        }
    }
    
    func fetchAllItems() async -> [LocalWatchlistItem] {
        guard let context = modelContext else { return [] }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistItem>(
                predicate: #Predicate { $0.isDeleted == false },
                sortBy: [SortDescriptor(\.sortIndex)]
            )
            return try context.fetch(descriptor)
        } catch {
            print("❌ Cache fetchAllItems error: \(error)")
            return []
        }
    }
    
    func fetchItems(groupId: String?) async -> [LocalWatchlistItem] {
        guard let context = modelContext else { return [] }
        
        do {
            var predicate: Predicate<LocalWatchlistItem>?
            if let groupId = groupId {
                predicate = #Predicate { $0.groupId == groupId && $0.isDeleted == false }
            } else {
                predicate = #Predicate { $0.groupId == nil && $0.isDeleted == false }
            }
            
            let descriptor = FetchDescriptor<LocalWatchlistItem>(
                predicate: predicate,
                sortBy: [SortDescriptor(\.sortIndex)]
            )
            return try context.fetch(descriptor)
        } catch {
            print("❌ Cache fetchItems error: \(error)")
            return []
        }
    }
    
    func deleteItem(fundCode: String) async {
        guard let context = modelContext else { return }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistItem>(
                predicate: #Predicate { $0.fundCode == fundCode }
            )
            
            if let item = try context.fetch(descriptor).first {
                context.delete(item)
                try context.save()
            }
        } catch {
            print("❌ Cache deleteItem error: \(error)")
        }
    }
    
    // MARK: - 分组操作
    
    func saveGroup(_ group: WatchlistGroup) async {
        guard let context = modelContext else { return }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistGroup>(
                predicate: #Predicate { $0.id == group.id }
            )
            
            if let existing = try context.fetch(descriptor).first {
                existing.name = group.name
                existing.icon = group.icon
                existing.color = group.color
                existing.sortIndex = Int32(group.sortIndex)
                existing.lastSyncTime = group.updatedAt
            } else {
                let localGroup = LocalWatchlistGroup(
                    id: group.id,
                    name: group.name,
                    icon: group.icon,
                    color: group.color,
                    sortIndex: Int32(group.sortIndex)
                )
                context.insert(localGroup)
            }
            
            try context.save()
        } catch {
            print("❌ Cache saveGroup error: \(error)")
        }
    }
    
    func saveGroups(_ groups: [WatchlistGroup]) async {
        for group in groups {
            await saveGroup(group)
        }
    }
    
    func fetchAllGroups() async -> [LocalWatchlistGroup] {
        guard let context = modelContext else { return [] }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistGroup>(
                sortBy: [SortDescriptor(\.sortIndex)]
            )
            return try context.fetch(descriptor)
        } catch {
            print("❌ Cache fetchAllGroups error: \(error)")
            return []
        }
    }
    
    func deleteGroup(id: String) async {
        guard let context = modelContext else { return }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistGroup>(
                predicate: #Predicate { $0.id == id }
            )
            
            if let group = try context.fetch(descriptor).first {
                context.delete(group)
                try context.save()
            }
        } catch {
            print("❌ Cache deleteGroup error: \(error)")
        }
    }
    
    // MARK: - 待同步操作
    
    func addPendingOperation(_ operation: PendingOperation) async {
        guard let context = modelContext else { return }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistItem>(
                predicate: #Predicate { $0.fundCode == operation.fundCode }
            )
            
            if let item = try context.fetch(descriptor).first {
                var ops = item.pendingOperations
                ops.append(operation)
                item.pendingOperations = ops
                try context.save()
            } else if operation.operationType == .add {
                // 如果是添加操作且项不存在，先创建项
                let newItem = LocalWatchlistItem(
                    fundCode: operation.fundCode,
                    fundName: operation.fundName ?? "",
                    groupId: operation.groupId,
                    sortIndex: operation.sortIndex != nil ? Int32(operation.sortIndex!) : 0
                )
                newItem.pendingOperations = [operation]
                context.insert(newItem)
                try context.save()
            }
        } catch {
            print("❌ Cache addPendingOperation error: \(error)")
        }
    }
    
    func getPendingOperations() async -> [PendingOperation] {
        guard let context = modelContext else { return [] }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistItem>()
            let items = try context.fetch(descriptor)
            
            var allOperations: [PendingOperation] = []
            for item in items {
                allOperations.append(contentsOf: item.pendingOperations)
            }
            
            return allOperations.sorted { $0.clientTimestamp < $1.clientTimestamp }
        } catch {
            print("❌ Cache getPendingOperations error: \(error)")
            return []
        }
    }
    
    func clearPendingOperations(for fundCode: String) async {
        guard let context = modelContext else { return }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistItem>(
                predicate: #Predicate { $0.fundCode == fundCode }
            )
            
            if let item = try context.fetch(descriptor).first {
                item.pendingOperations = []
                try context.save()
            }
        } catch {
            print("❌ Cache clearPendingOperations error: \(error)")
        }
    }
    
    func clearAllPendingOperations() async {
        guard let context = modelContext else { return }
        
        do {
            let descriptor = FetchDescriptor<LocalWatchlistItem>()
            let items = try context.fetch(descriptor)
            
            for item in items {
                item.pendingOperations = []
            }
            
            try context.save()
        } catch {
            print("❌ Cache clearAllPendingOperations error: \(error)")
        }
    }
}
