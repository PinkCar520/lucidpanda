// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/WatchlistModels.swift
import Foundation

// MARK: - 分组模型

public struct WatchlistGroup: Codable, Identifiable, Equatable {
    public let id: String
    public let userId: String
    public let name: String
    public let icon: String
    public let color: String
    public let sortIndex: Int
    public let createdAt: Date
    public let updatedAt: Date
    
    public init(
        id: String,
        userId: String,
        name: String,
        icon: String,
        color: String,
        sortIndex: Int,
        createdAt: Date,
        updatedAt: Date
    ) {
        self.id = id
        self.userId = userId
        self.name = name
        self.icon = icon
        self.color = color
        self.sortIndex = sortIndex
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
    
    enum CodingKeys: String, CodingKey {
        case id, userId = "user_id", name, icon, color
        case sortIndex = "sort_index"
        case createdAt = "created_at", updatedAt = "updated_at"
    }
}

// MARK: - 自选列表项

public struct WatchlistItem: Codable, Identifiable, Equatable {
    public let id: String
    public let userId: String
    public let fundCode: String
    public let fundName: String
    public let groupId: String?
    public let sortIndex: Int
    public let createdAt: Date
    public let updatedAt: Date
    public let isDeleted: Bool
    
    public init(
        id: String,
        userId: String,
        fundCode: String,
        fundName: String,
        groupId: String?,
        sortIndex: Int,
        createdAt: Date,
        updatedAt: Date,
        isDeleted: Bool
    ) {
        self.id = id
        self.userId = userId
        self.fundCode = fundCode
        self.fundName = fundName
        self.groupId = groupId
        self.sortIndex = sortIndex
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.isDeleted = isDeleted
    }
    
    enum CodingKeys: String, CodingKey {
        case id, userId = "user_id"
        case fundCode = "fund_code", fundName = "fund_name"
        case groupId = "group_id", sortIndex = "sort_index"
        case createdAt = "created_at", updatedAt = "updated_at"
        case isDeleted = "is_deleted"
    }
}

// MARK: - 同步操作类型

public enum SyncOperationType: String, Codable {
    case add = "ADD"
    case remove = "REMOVE"
    case update = "UPDATE"
    case reorder = "REORDER"
    case moveGroup = "MOVE_GROUP"
}

// MARK: - 待同步操作

public struct PendingOperation: Codable {
    public let id: String
    public let operationType: SyncOperationType
    public let fundCode: String
    public let fundName: String?
    public let groupId: String?
    public let sortIndex: Int?
    public let clientTimestamp: Date
    public let deviceId: String
    
    public init(
        id: String = UUID().uuidString,
        operationType: SyncOperationType,
        fundCode: String,
        fundName: String? = nil,
        groupId: String? = nil,
        sortIndex: Int? = nil,
        deviceId: String = "iOS"
    ) {
        self.id = id
        self.operationType = operationType
        self.fundCode = fundCode
        self.fundName = fundName
        self.groupId = groupId
        self.sortIndex = sortIndex
        self.clientTimestamp = Date()
        self.deviceId = deviceId
    }
    
    enum CodingKeys: String, CodingKey {
        case id, operationType = "operation_type", fundCode = "fund_code"
        case fundName = "fund_name", groupId = "group_id"
        case sortIndex = "sort_index", clientTimestamp = "client_timestamp", deviceId = "device_id"
    }
}

// MARK: - 同步请求

public struct SyncRequest: Codable {
    public let operations: [PendingOperation]
    public let lastSyncTime: Date?
    
    public init(operations: [PendingOperation], lastSyncTime: Date?) {
        self.operations = operations
        self.lastSyncTime = lastSyncTime
    }
    
    enum CodingKeys: String, CodingKey {
        case operations, lastSyncTime = "last_sync_time"
    }
}

// MARK: - 同步结果

public struct SyncResult: Codable {
    public let operation: String
    public let fundCode: String
    public let success: Bool
    public let error: String?
    
    enum CodingKeys: String, CodingKey {
        case operation, fundCode = "fund_code", success, error
    }
}

// MARK: - API 响应

public struct WatchlistGroupsResponse: Codable {
    public let data: [WatchlistGroup]
}

public struct WatchlistItemsResponse: Codable {
    public let data: [WatchlistItem]
    public let groups: [WatchlistGroup]
    public let syncTime: String?
    
    enum CodingKeys: String, CodingKey {
        case data, groups
        case syncTime = "sync_time"
    }
}

public struct SyncResponse: Codable {
    public let results: [SyncResult]
}

public struct WatchlistCreateGroupRequest: Codable {
    public let name: String
    public let icon: String
    public let color: String
    public let sortIndex: Int
    
    enum CodingKeys: String, CodingKey {
        case name, icon, color
        case sortIndex = "sort_index"
    }
    
    public init(name: String, icon: String = "folder", color: String = "#007AFF", sortIndex: Int = 0) {
        self.name = name
        self.icon = icon
        self.color = color
        self.sortIndex = sortIndex
    }
}

public struct WatchlistMoveGroupRequest: Codable {
    public let groupId: String?
    
    public init(groupId: String?) {
        self.groupId = groupId
    }
    
    enum CodingKeys: String, CodingKey {
        case groupId = "group_id"
    }
}

public struct WatchlistReorderItem: Codable {
    public let fundCode: String
    public let sortIndex: Int
    
    enum CodingKeys: String, CodingKey {
        case fundCode = "fund_code"
        case sortIndex = "sort_index"
    }
}

public struct WatchlistReorderRequest: Codable {
    public let items: [WatchlistReorderItem]
}

public struct WatchlistBatchAddRequest: Codable {
    public let items: [WatchlistBatchItem]
    
    public init(items: [WatchlistBatchItem]) {
        self.items = items
    }
}

public struct WatchlistBatchItem: Codable {
    public let code: String
    public let name: String
    public let groupId: String?
    
    public init(code: String, name: String, groupId: String?) {
        self.code = code
        self.name = name
        self.groupId = groupId
    }
    
    enum CodingKeys: String, CodingKey {
        case code, name
        case groupId = "group_id"
    }
}

public struct WatchlistBatchRemoveRequest: Codable {
    public let codes: [String]
    
    public init(codes: [String]) {
        self.codes = codes
    }
}
