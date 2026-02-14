import Foundation
import Observation
import SwiftUI

@Observable
public class AppRootViewModel {
    public enum AppState {
        case loading
        case unauthenticated
        case authenticated
    }
    
    public var currentState: AppState = .loading
    
    public init() {}
    
    @MainActor
    public func checkAuthentication() async {
        // 预留 1 秒展示液态加载动画，提升品牌感
        try? await Task.sleep(nanoseconds: 1_000_000_000)
        
        if AuthTokenStore.accessToken() != nil || AuthTokenStore.refreshToken() != nil {
            withAnimation(.spring()) {
                currentState = .authenticated
            }
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
    }
}
