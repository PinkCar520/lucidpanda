import Foundation
import Observation
import AlphaCore
import AlphaData

@Observable
class LoginViewModel {
    var email = ""
    var password = ""
    var isLoading = false
    var isPasskeyLoading = false
    var errorMessage: String?
    var canSubmit: Bool { !email.isEmpty && !password.isEmpty }
    
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
            
            // 安全存储 Token 到 Keychain
            try storeToken(result.accessToken)
            
            print("Login Success for: \(result.user.email)")
            onSuccess?()
            
        } catch {
            errorMessage = NSLocalizedString("auth.error.invalid_credentials", comment: "")
            print("Login error: \(error)")
        }
        
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
            try storeToken(result.accessToken)
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
    
    private func storeToken(_ token: String) throws {
        if let tokenData = token.data(using: .utf8) {
            try KeychainManager.shared.save(key: "access_token", data: tokenData)
        }
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
