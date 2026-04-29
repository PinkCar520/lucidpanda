import Foundation
import Observation
import SwiftUI
import AlphaCore
import OSLog

public struct UserProfileDTO: Codable {
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
    public let isPro: Bool?
    public let proExpiresAt: Date?

    public enum CodingKeys: String, CodingKey {
        case id, email, username, name, nickname, gender, birthday, location
        case languagePreference = "language_preference"
        case displayName = "display_name"
        case createdAt = "created_at"
        case avatarUrl = "avatar_url"
        case isTwoFaEnabled = "is_two_fa_enabled"
        case isPro = "is_pro"
        case proExpiresAt = "pro_expires_at"
    }
}

@Observable
public class AppRootViewModel {
    private let logger = AppLog.root
    private let profileCacheKey = "com.pincar.cache.user_profile"
    
    public enum AppState {
        case loading
        case unauthenticated
        case authenticated
    }
    
    public var currentState: AppState = .loading
    public var userProfile: UserProfileDTO?
    public var marketPulseViewModel = MarketPulseViewModel()

    public var isPro: Bool {
        guard let profile = userProfile else { return false }
        if let pro = profile.isPro, pro == true {
            if let expiry = profile.proExpiresAt {
                return expiry > Date()
            }
            return true
        }
        return false
    }
    
    public init() {
        loadProfileFromCache()
    }
    
    private func loadProfileFromCache() {
        if let data = UserDefaults.standard.data(forKey: profileCacheKey),
           let cached = try? JSONDecoder().decode(UserProfileDTO.self, from: data) {
            self.userProfile = cached
        }
    }
    
    private func saveProfileToCache(_ profile: UserProfileDTO) {
        if let data = try? JSONEncoder().encode(profile) {
            UserDefaults.standard.set(data, forKey: profileCacheKey)
        }
    }
    
    @MainActor
    public func checkAuthentication() async {
        // 直接进行极速鉴权判断以实现“无感秒开”
        if AuthTokenStore.accessToken() != nil || AuthTokenStore.refreshToken() != nil {
            withAnimation(.easeOut(duration: 0.2)) {
                currentState = .authenticated
            }
            Task { 
                await fetchUserProfile()
                await marketPulseViewModel.start()
            }
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
                UserDefaults.standard.removeObject(forKey: profileCacheKey)
            }
            return
        }

        if newState == .unauthenticated {
            WatchlistSyncEngine.shared.stop()
            marketPulseViewModel.stop()
            Task { await SSEResolver.shared.stop() }
            AuthTokenStore.clear()
            userProfile = nil
            UserDefaults.standard.removeObject(forKey: profileCacheKey)
        }
        withAnimation(.easeOut(duration: 0.2)) {
            self.currentState = newState
        }
        
        if newState == .authenticated {
            Task { 
                await fetchUserProfile() 
                await marketPulseViewModel.start()
            }
        }
    }
    
    @MainActor
    public func fetchUserProfile() async {
        guard currentState == .authenticated else { return }
        guard AuthTokenStore.accessToken() != nil || AuthTokenStore.refreshToken() != nil else { return }

        do {
            let profile: UserProfileDTO = try await APIClient.shared.fetch(path: "/api/v1/auth/me")
            saveProfileToCache(profile)
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
