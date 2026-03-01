import Foundation
import Observation
import SwiftUI
import AlphaCore
import OSLog

public struct UserProfileDTO: Decodable {
    public let id: String
    public let email: String
    public let username: String?
    public let name: String?
    public let nickname: String?
    public let gender: String?
    public let birthday: String?      // "YYYY-MM-DD"
    public let location: String?
    public let languagePreference: String?
    public let displayName: String?
    public let createdAt: Date?
    public let avatarUrl: String?
    public let isTwoFaEnabled: Bool?

    public enum CodingKeys: String, CodingKey {
        case id, email, username, name, nickname, gender, birthday, location
        case languagePreference = "language_preference"
        case displayName = "display_name"
        case createdAt = "created_at"
        case avatarUrl = "avatar_url"
        case isTwoFaEnabled = "is_two_fa_enabled"
    }
}

@Observable
public class AppRootViewModel {
    private let logger = AppLog.root
    public enum AppState {
        case loading
        case unauthenticated
        case authenticated
    }
    
    public var currentState: AppState = .loading
    public var userProfile: UserProfileDTO?
    
    public init() {}
    
    @MainActor
    public func checkAuthentication() async {
        // 直接进行极速鉴权判断以实现“无感秒开”
        if AuthTokenStore.accessToken() != nil || AuthTokenStore.refreshToken() != nil {
            withAnimation(.easeOut(duration: 0.2)) {
                currentState = .authenticated
            }
            Task { await fetchUserProfile() }
        } else {
            withAnimation(.easeOut(duration: 0.2)) {
                currentState = .unauthenticated
            }
        }
    }
    
    @MainActor
    public func updateState(to newState: AppState) {
        if currentState == newState {
            if newState == .unauthenticated {
                userProfile = nil
            }
            return
        }

        if newState == .unauthenticated {
            WatchlistSyncEngine.shared.stop()
            Task { await SSEResolver.shared.stop() }
            AuthTokenStore.clear()
        }
        withAnimation(.easeOut(duration: 0.2)) {
            self.currentState = newState
        }
        
        if newState == .authenticated {
            Task { await fetchUserProfile() }
        } else {
            self.userProfile = nil
        }
    }
    
    @MainActor
    public func fetchUserProfile() async {
        guard currentState == .authenticated else { return }
        guard AuthTokenStore.accessToken() != nil || AuthTokenStore.refreshToken() != nil else { return }

        do {
            let profile: UserProfileDTO = try await APIClient.shared.fetch(path: "/api/v1/auth/me")
            withAnimation(.easeOut(duration: 0.2)) {
                self.userProfile = profile
            }
        } catch {
            if case APIError.unauthorized = error {
                return
            }
            logger.error("Failed to fetch user profile: \(error.localizedDescription, privacy: .public)")
        }
    }
}
