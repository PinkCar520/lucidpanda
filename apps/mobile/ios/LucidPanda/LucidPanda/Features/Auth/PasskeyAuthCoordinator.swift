import Foundation
import AuthenticationServices
import UIKit

enum PasskeyAuthError: Error {
    case unsupported
    case invalidChallenge
    case cancelled
    case unknown
}

@MainActor
final class PasskeyAuthCoordinator {
    static func authenticate(
        challengeBase64URL: String,
        rpId: String,
        allowedCredentialIDs: [String]
    ) async throws -> [String: Any] {
        guard #available(iOS 16.0, *) else {
            throw PasskeyAuthError.unsupported
        }
        
        guard let challenge = Data(base64URLEncoded: challengeBase64URL) else {
            throw PasskeyAuthError.invalidChallenge
        }
        
        let provider = ASAuthorizationPlatformPublicKeyCredentialProvider(relyingPartyIdentifier: rpId)
        let request = provider.createCredentialAssertionRequest(challenge: challenge)
        
        let descriptors = allowedCredentialIDs
            .compactMap { Data(base64URLEncoded: $0) }
            .map { ASAuthorizationPlatformPublicKeyCredentialDescriptor(credentialID: $0) }
        if !descriptors.isEmpty {
            request.allowedCredentials = descriptors
        }
        
        let executor = PasskeyAssertionExecutor(request: request)
        return try await executor.execute()
    }
}

@MainActor
private final class PasskeyAssertionExecutor: NSObject, ASAuthorizationControllerDelegate, ASAuthorizationControllerPresentationContextProviding {
    private let controller: ASAuthorizationController
    private var continuation: CheckedContinuation<[String: Any], Error>?
    
    init(request: ASAuthorizationPlatformPublicKeyCredentialAssertionRequest) {
        self.controller = ASAuthorizationController(authorizationRequests: [request])
        super.init()
        self.controller.delegate = self
        self.controller.presentationContextProvider = self
    }
    
    func execute() async throws -> [String: Any] {
        try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            self.controller.performRequests()
        }
    }
    
    func authorizationController(controller: ASAuthorizationController, didCompleteWithAuthorization authorization: ASAuthorization) {
        guard let credential = authorization.credential as? ASAuthorizationPlatformPublicKeyCredentialAssertion else {
            continuation?.resume(throwing: PasskeyAuthError.unknown)
            continuation = nil
            return
        }
        
        var response: [String: Any] = [
            "clientDataJSON": credential.rawClientDataJSON.base64URLEncodedString(),
            "authenticatorData": credential.rawAuthenticatorData.base64URLEncodedString(),
            "signature": credential.signature.base64URLEncodedString(),
        ]
        
        if let userID = credential.userID {
            response["userHandle"] = userID.base64URLEncodedString()
        } else {
            response["userHandle"] = NSNull()
        }
        
        let payload: [String: Any] = [
            "id": credential.credentialID.base64URLEncodedString(),
            "rawId": credential.credentialID.base64URLEncodedString(),
            "type": "public-key",
            "response": response,
            "clientExtensionResults": [:]
        ]
        
        continuation?.resume(returning: payload)
        continuation = nil
    }
    
    func authorizationController(controller: ASAuthorizationController, didCompleteWithError error: Error) {
        if let authError = error as? ASAuthorizationError, authError.code == .canceled {
            continuation?.resume(throwing: PasskeyAuthError.cancelled)
        } else {
            continuation?.resume(throwing: error)
        }
        continuation = nil
    }
    
    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        let scenes = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }

        if let window = scenes
                .flatMap({ $0.windows })
                .first(where: \.isKeyWindow) {
            return window
        }

        if let scene = scenes.first(where: { $0.activationState == .foregroundActive }) {
            return ASPresentationAnchor(windowScene: scene)
        }

        guard let scene = scenes.first else {
            fatalError("No UIWindowScene available for presentation anchor.")
        }
        return ASPresentationAnchor(windowScene: scene)
    }
}

private extension Data {
    init?(base64URLEncoded input: String) {
        var base64 = input
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        
        let remainder = base64.count % 4
        if remainder > 0 {
            base64 += String(repeating: "=", count: 4 - remainder)
        }
        
        self.init(base64Encoded: base64)
    }
    
    func base64URLEncodedString() -> String {
        self.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}
