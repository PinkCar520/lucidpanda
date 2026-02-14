import Foundation
import AlphaData

enum AuthTokenStore {
    private static let accessTokenKey = "access_token"
    private static let refreshTokenKey = "refresh_token"
    private static let accessTokenExpiryKey = "access_token_expires_at"

    static func saveSession(accessToken: String, refreshToken: String, expiresIn: Int?) throws {
        if let accessData = accessToken.data(using: .utf8) {
            try KeychainManager.shared.save(key: accessTokenKey, data: accessData)
        }
        if let refreshData = refreshToken.data(using: .utf8) {
            try KeychainManager.shared.save(key: refreshTokenKey, data: refreshData)
        }
        if let expiresIn {
            let expiresAt = Date().addingTimeInterval(TimeInterval(expiresIn))
            let rawValue = String(expiresAt.timeIntervalSince1970)
            if let expiryData = rawValue.data(using: .utf8) {
                try KeychainManager.shared.save(key: accessTokenExpiryKey, data: expiryData)
            }
        }
    }

    static func accessToken() -> String? {
        guard let data = try? KeychainManager.shared.read(key: accessTokenKey) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func refreshToken() -> String? {
        guard let data = try? KeychainManager.shared.read(key: refreshTokenKey) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func accessTokenExpiry() -> Date? {
        guard let data = try? KeychainManager.shared.read(key: accessTokenExpiryKey),
              let rawValue = String(data: data, encoding: .utf8),
              let timestamp = TimeInterval(rawValue) else {
            return nil
        }
        return Date(timeIntervalSince1970: timestamp)
    }

    static func clear() {
        try? KeychainManager.shared.delete(key: accessTokenKey)
        try? KeychainManager.shared.delete(key: refreshTokenKey)
        try? KeychainManager.shared.delete(key: accessTokenExpiryKey)
    }
}
