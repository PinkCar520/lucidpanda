// mobile/ios/Packages/AlphaData/Sources/AlphaData/AuthModels.swift
import Foundation

public struct UserDTO: Codable {
    public let id: UUID
    public let email: String
    public let name: String?
    public let role: String
    public let isActive: Bool
    public let isVerified: Bool
    public let createdAt: Date
    public let avatarUrl: String?
    public let nickname: String?
    public let gender: String?
    public let birthday: String?
    public let location: String?
    public let languagePreference: String?
    public let timezone: String?
    public let themePreference: String?
    public let phoneNumber: String?
    public let isPhoneVerified: Bool
    public let isTwoFaEnabled: Bool
    
    enum CodingKeys: String, CodingKey {
        case id, email, name, role, nickname, gender, birthday, location, timezone
        case isActive = "is_active"
        case isVerified = "is_verified"
        case createdAt = "created_at"
        case avatarUrl = "avatar_url"
        case languagePreference = "language_preference"
        case themePreference = "theme_preference"
        case phoneNumber = "phone_number"
        case isPhoneVerified = "is_phone_verified"
        case isTwoFaEnabled = "is_two_fa_enabled"
    }
}

public struct LoginResponseDTO: Codable {
    public let accessToken: String
    public let refreshToken: String
    public let tokenType: String
    public let user: UserDTO
    public let expiresIn: Int?
    
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case user
        case expiresIn = "expires_in"
    }
}
