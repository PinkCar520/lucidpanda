import Foundation
import Observation
import SwiftUI
import AlphaCore

public struct UserProfileDTO: Decodable {
    public let id: String
    public let email: String
    public let displayName: String?
    public let createdAt: Date?
    public let avatarUrl: String?
    
    public enum CodingKeys: String, CodingKey {
        case id, email
        case displayName = "display_name"
        case createdAt = "created_at"
        case avatarUrl = "avatar_url"
    }
}

@Observable
public class AppRootViewModel {
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
        // 预留 1 秒展示液态加载动画，提升品牌感
        try? await Task.sleep(nanoseconds: 1_000_000_000)
        
        if AuthTokenStore.accessToken() != nil || AuthTokenStore.refreshToken() != nil {
            withAnimation(.spring()) {
                currentState = .authenticated
            }
            Task { await fetchUserProfile() }
        } else {
            withAnimation(.spring()) {
                currentState = .unauthenticated
            }
        }
    }
    
    @MainActor
    public func updateState(to newState: AppState) {
        if newState == .unauthenticated {
            AuthTokenStore.clear()
        }
        withAnimation(.spring(response: 0.6, dampingFraction: 0.8)) {
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
        do {
            let profile: UserProfileDTO = try await APIClient.shared.fetch(path: "/api/v1/auth/me")
            withAnimation(.spring()) {
                self.userProfile = profile
            }
        } catch {
            print("❌ AppRootViewModel Failed to fetch user profile: \(error)")
        }
    }
}
