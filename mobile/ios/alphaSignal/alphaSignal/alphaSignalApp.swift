import SwiftUI
import AlphaDesign
import AlphaCore
import AlphaData
import SwiftData

@main
struct alphaSignalApp: App {
    // 全局状态管理
    @State private var rootViewModel = AppRootViewModel()
    
    // 初始化 SwiftData 容器
    var sharedModelContainer: ModelContainer = {
        let schema = Schema([
            IntelligenceModel.self,
        ])
        let modelConfiguration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)

        do {
            return try ModelContainer(for: schema, configurations: [modelConfiguration])
        } catch {
            fatalError("Could not create ModelContainer: \(error)")
        }
    }()
    
    init() {
        setupAPIClient()
        AlarmNotificationManager.shared.requestPermissions()
    }
    
    var body: some Scene {
        WindowGroup {
            Group {
                switch rootViewModel.currentState {
                case .loading:
                    // 启动闪屏
                    ZStack {
                        LiquidBackground()
                        VStack(spacing: 20) {
                            ProgressView()
                                .tint(.primary)
                                .scaleEffect(1.5)
                            Text("正在初始化安全链路...")
                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                .foregroundStyle(.secondary)
                        }
                    }
                    
                case .unauthenticated:
                    // 登录页
                    LoginView()
                        .environment(rootViewModel)
                    
                case .authenticated:
                    // 进入全功能主终端
                    MainTabView()
                        .environment(rootViewModel)
                }
            }
            .task {
                // 启动时检查身份
                await rootViewModel.checkAuthentication()
            }
        }
        .modelContainer(sharedModelContainer) // 注入容器
    }
    
    private func setupAPIClient() {
        // 注入会话 Token 提供与更新逻辑
        Task {
            await APIClient.shared.setTokenProvider {
                AuthTokenStore.accessToken()
            }
            await APIClient.shared.setRefreshTokenProvider {
                AuthTokenStore.refreshToken()
            }
            await APIClient.shared.setAccessTokenExpiryProvider {
                AuthTokenStore.accessTokenExpiry()
            }
            await APIClient.shared.setSessionUpdater { accessToken, refreshToken, expiresIn in
                try? AuthTokenStore.saveSession(
                    accessToken: accessToken,
                    refreshToken: refreshToken,
                    expiresIn: expiresIn
                )
            }
            
            // 注入 401 自动登出逻辑
            await APIClient.shared.setOnUnauthorized {
                rootViewModel.updateState(to: .unauthenticated)
            }
        }
    }
}
