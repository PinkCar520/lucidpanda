// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/SecurityModels.swift
import Foundation

public struct AuthAuditLog: Codable, Identifiable {
    public let id: Int
    public let action: String
    public let ipAddress: String
    public let userAgent: String?
    public let details: [String: String]?
    public let createdAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, action, details
        case ipAddress = "ip_address"
        case userAgent = "user_agent"
        case createdAt = "created_at"
    }
}

public struct SessionDTO: Codable, Identifiable {
    public let id: Int
    public let deviceInfo: [String: String]?
    public let ipAddress: String
    public let createdAt: Date
    public let lastActiveAt: Date?
    public let isCurrent: Bool
    
    enum CodingKeys: String, CodingKey {
        case id, createdAt, isCurrent
        case deviceInfo = "device_info"
        case ipAddress = "ip_address"
        case lastActiveAt = "last_active_at"
    }
}
