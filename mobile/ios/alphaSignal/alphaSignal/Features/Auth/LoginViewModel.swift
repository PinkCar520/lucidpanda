import Foundation
import Observation
import AlphaCore
import AlphaData

enum AuthMode {
    case login
    case register
    case forgotPassword
}

@Observable
class LoginViewModel {
    var mode: AuthMode = .login
    
    var email = ""
    var password = ""
    var confirmPassword = ""
    
    var isLoading = false
    var isPasskeyLoading = false
    var errorMessage: String?
    var successMessage: String?
    
    var canSubmit: Bool { 
        if mode == .forgotPassword { return !email.isEmpty }
        if mode == .register { return !email.isEmpty && !password.isEmpty && password == confirmPassword }
        return !email.isEmpty && !password.isEmpty 
    }
    
    // 回调闭包，用于登录成功后通知 Root 视图
    var onSuccess: (() -> Void)?
    
    @MainActor
    func performLogin() async {
        guard !email.isEmpty && !password.isEmpty else {
            errorMessage = NSLocalizedString("auth.validation.missing_credentials", comment: "")
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
            
            // 安全存储会话 Token 到 Keychain
            try storeSession(from: result)
            
            print("Login Success for: \(result.user.email)")
            onSuccess?()
            
        } catch {
            errorMessage = "登录失败：邮箱或密码错误"
            print("Login error: \(error)")
        }
        
        isLoading = false
    }
    
    @MainActor
    func performRegister() async {
        guard canSubmit else {
            errorMessage = "请检查输入的信息格式"
            return
        }
        isLoading = true
        errorMessage = nil
        successMessage = nil
        
        // 模拟请求延迟
        try? await Task.sleep(nanoseconds: 1_200_000_000)
        
        // TODO: Backend implementation for Register
        successMessage = "注册成功"
        isLoading = false
    }
    
    @MainActor
    func performPasswordReset() async {
        guard !email.isEmpty else {
            errorMessage = "请输入有效的电子邮箱"
            return
        }
        isLoading = true
        errorMessage = nil
        successMessage = nil
        
        // 模拟请求延迟
        try? await Task.sleep(nanoseconds: 1_000_000_000)
        
        // TODO: Backend implementation for Forgot Password
        successMessage = "重置密码指令已发送至您的邮箱"
        isLoading = false
    }
    
    @MainActor
    func performPasskeyLogin() async {
        guard !isPasskeyLoading else { return }
        
        isPasskeyLoading = true
        errorMessage = nil
        
        do {
            let options: PasskeyLoginOptionsDTO = try await APIClient.shared.fetch(
                path: "/api/v1/auth/passkeys/login/options",
                method: "POST"
            )
            
            let assertion = try await PasskeyAuthCoordinator.authenticate(
                challengeBase64URL: options.challenge,
                rpId: options.rpId,
                allowedCredentialIDs: options.allowCredentials?.map(\.id) ?? []
            )
            
            let payload: [String: Any] = [
                "auth_data": assertion,
                "state": options.state
            ]
            let body = try JSONSerialization.data(withJSONObject: payload, options: [])
            let endpoint = RawEndpoint(path: "/api/v1/auth/passkeys/login/verify", method: .post, body: body)
            
            let result: LoginResponseDTO = try await APIClient.shared.request(endpoint)
            try storeSession(from: result)
            onSuccess?()
        } catch PasskeyAuthError.cancelled {
            // Keep silent on user-cancelled passkey sheet.
        } catch PasskeyAuthError.unsupported {
            errorMessage = NSLocalizedString("auth.passkey.unsupported", comment: "")
        } catch {
            errorMessage = NSLocalizedString("auth.passkey.failed", comment: "")
            print("Passkey login error: \(error)")
        }
        
        isPasskeyLoading = false
    }
    
    private func storeSession(from result: LoginResponseDTO) throws {
        try AuthTokenStore.saveSession(
            accessToken: result.accessToken,
            refreshToken: result.refreshToken,
            expiresIn: result.expiresIn
        )
    }
}

private struct PasskeyLoginOptionsDTO: Decodable {
    let challenge: String
    let rpId: String
    let state: String
    let allowCredentials: [PasskeyAllowedCredentialDTO]?
}

private struct PasskeyAllowedCredentialDTO: Decodable {
    let id: String
}

private struct RawEndpoint: Endpoint {
    let path: String
    let method: HTTPMethod
    let body: Data?
}
