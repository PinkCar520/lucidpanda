import Foundation
import Observation
import AlphaData
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
        
        do {
            _ = try KeychainManager.shared.read(key: "access_token")
            withAnimation(.spring()) {
                currentState = .authenticated
            }
        } catch {
            withAnimation(.spring()) {
                currentState = .unauthenticated
            }
        }
    }
    
    @MainActor
    public func updateState(to newState: AppState) {
        withAnimation(.spring(response: 0.6, dampingFraction: 0.8)) {
            self.currentState = newState
        }
    }
}
