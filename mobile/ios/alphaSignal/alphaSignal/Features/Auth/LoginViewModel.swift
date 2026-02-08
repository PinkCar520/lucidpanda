import Foundation
import Observation
import AlphaCore
import AlphaData

@Observable
class LoginViewModel {
    var email = ""
    var password = ""
    var isLoading = false
    var errorMessage: String?
    
    // 回调闭包，用于登录成功后通知 Root 视图
    var onSuccess: (() -> Void)?
    
    @MainActor
    func performLogin() async {
        guard !email.isEmpty && !password.isEmpty else {
            errorMessage = "请输入完整凭据"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            let result: LoginResponseDTO = try await APIClient.shared.authRequest(
                path: "/api/v1/auth/login",
                formData: [
                    "username": email,
                    "password": password
                ]
            )
            
            // 安全存储 Token 到 Keychain
            if let tokenData = result.accessToken.data(using: .utf8) {
                try KeychainManager.shared.save(key: "access_token", data: tokenData)
            }
            
            print("Login Success for: \(result.user.email)")
            onSuccess?()
            
        } catch {
            errorMessage = "身份验证失败，请检查邮箱或密码"
            print("Login error: \(error)")
        }
        
        isLoading = false
    }
}
