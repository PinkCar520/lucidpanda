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
                                .tint(.white)
                                .scaleEffect(1.5)
                            Text("正在初始化安全链路...")
                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                .foregroundStyle(.white.opacity(0.5))
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
            .preferredColorScheme(.light) // 强制浅色模式以符合 Web 纯净风格
        }
        .modelContainer(sharedModelContainer) // 注入容器
    }
    
    private func setupAPIClient() {
        // 注入 Token 提供者
        Task {
            await APIClient.shared.setTokenProvider {
                if let data = try? KeychainManager.shared.read(key: "access_token") {
                    return String(data: data, encoding: .utf8)
                }
                return nil
            }
            
            // 注入 401 自动登出逻辑
            await APIClient.shared.setOnUnauthorized {
                rootViewModel.updateState(to: .unauthenticated)
            }
        }
    }
}