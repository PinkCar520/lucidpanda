import Foundation
import Observation
import AlphaCore
import AlphaData
import OSLog

enum AuthMode {
    case login
    case register
    case forgotPassword
}

@Observable
class LoginViewModel {
    private let logger = AppLog.auth
    var mode: AuthMode = .login
    
    var email = ""
    var username = ""
    var password = ""
    var confirmPassword = ""
    
    var isLoading = false
    var isPasskeyLoading = false
    var errorMessage: String?
    var successMessage: String?
    
    var canSubmit: Bool { 
        if mode == .forgotPassword { return !email.isEmpty }
        if mode == .register {
            return !email.isEmpty
                && !username.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                && !password.isEmpty
                && password.count >= 8
                && password == confirmPassword
        }
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
            
            logger.info("Login success for \(result.user.email, privacy: .private)")
            onSuccess?()
            
        } catch {
            errorMessage = NSLocalizedString("auth.error.invalid_credentials", comment: "")
            logger.error("Login failed: \(error.localizedDescription, privacy: .public)")
        }
        
        isLoading = false
    }
    
    @MainActor
    func performRegister() async {
        guard canSubmit else {
            errorMessage = NSLocalizedString("auth.validation.invalid_format", comment: "")
            return
        }
        isLoading = true
        errorMessage = nil
        successMessage = nil

        do {
            let request = RegisterRequest(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                username: username.trimmingCharacters(in: .whitespacesAndNewlines),
                password: password
            )
            let _: UserDTO = try await APIClient.shared.send(
                path: "/api/v1/auth/register",
                method: "POST",
                body: request
            )
            successMessage = NSLocalizedString("auth.success.registered", comment: "")
            mode = .login
            password = ""
            confirmPassword = ""
        } catch {
            errorMessage = parseFriendlyError(error, fallback: NSLocalizedString("auth.error.register_failed", comment: ""))
            logger.error("Register failed: \(error.localizedDescription, privacy: .public)")
        }

        isLoading = false
    }
    
    @MainActor
    func performPasswordReset() async {
        guard !email.isEmpty else {
            errorMessage = NSLocalizedString("auth.validation.invalid_email", comment: "")
            return
        }
        isLoading = true
        errorMessage = nil
        successMessage = nil

        do {
            let request = ForgotPasswordRequest(email: email.trimmingCharacters(in: .whitespacesAndNewlines))
            let response: MessageResponseDTO = try await APIClient.shared.send(
                path: "/api/v1/auth/forgot-password",
                method: "POST",
                body: request
            )
            successMessage = response.message
        } catch {
            errorMessage = parseFriendlyError(error, fallback: NSLocalizedString("auth.error.forgot_password_failed", comment: ""))
            logger.error("Forgot password failed: \(error.localizedDescription, privacy: .public)")
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
            try storeSession(from: result)
            onSuccess?()
        } catch PasskeyAuthError.cancelled {
            // Keep silent on user-cancelled passkey sheet.
        } catch PasskeyAuthError.unsupported {
            errorMessage = NSLocalizedString("auth.passkey.unsupported", comment: "")
        } catch {
            errorMessage = NSLocalizedString("auth.passkey.failed", comment: "")
            logger.error("Passkey login failed: \(error.localizedDescription, privacy: .public)")
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

    private func parseFriendlyError(_ error: Error, fallback: String) -> String {
        guard case let APIError.serverError(_, message) = error else {
            return fallback
        }
        guard let message, !message.isEmpty else { return fallback }

        if let data = message.data(using: .utf8),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let detail = json["detail"] as? String,
           !detail.isEmpty {
            return detail
        }

        return message
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

private struct RegisterRequest: Encodable {
    let email: String
    let username: String
    let password: String
}

private struct ForgotPasswordRequest: Encodable {
    let email: String
}

private struct MessageResponseDTO: Decodable {
    let message: String
}
