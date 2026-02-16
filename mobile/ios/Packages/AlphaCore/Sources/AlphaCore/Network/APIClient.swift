import Foundation
import OSLog

public actor APIClient {
    public static let shared = APIClient()
    private let session = URLSession.shared
    private let logger = Logger(subsystem: "com.pincar.alphasignal", category: "APIClient")
    
    // 会话回调，避免与上层存储实现耦合
    private var tokenProvider: (() async -> String?)?
    private var refreshTokenProvider: (() async -> String?)?
    private var accessTokenExpiryProvider: (() async -> Date?)?
    private var sessionUpdater: ((_ accessToken: String, _ refreshToken: String, _ expiresIn: Int?) async -> Void)?
    private var onUnauthorized: (() async -> Void)?
    
    public func setTokenProvider(_ provider: @escaping () async -> String?) {
        self.tokenProvider = provider
    }

    public func setRefreshTokenProvider(_ provider: @escaping () async -> String?) {
        self.refreshTokenProvider = provider
    }

    public func setAccessTokenExpiryProvider(_ provider: @escaping () async -> Date?) {
        self.accessTokenExpiryProvider = provider
    }

    public func setSessionUpdater(_ updater: @escaping (_ accessToken: String, _ refreshToken: String, _ expiresIn: Int?) async -> Void) {
        self.sessionUpdater = updater
    }
    
    public func setOnUnauthorized(_ handler: @escaping () async -> Void) {
        self.onUnauthorized = handler
    }
    
    #if DEBUG
    private let baseURL = URL(string: "http://43.139.108.187:8001")! // TODO: Change to https when SSL is configured on server
    #else
    private let baseURL = URL(string: "http://43.139.108.187:8001")! // TODO: Change to https when SSL is configured on server
    #endif

    public func authRequest<T: Decodable>(path: String, formData: [String: String]) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw APIError.invalidURL }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        
        let bodyString = formData.map { "\($0.key)=\($0.value)" }.joined(separator: "&")
        request.httpBody = bodyString.data(using: .utf8)
        
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        
        if httpResponse.statusCode != 200 {
            throw APIError.serverError(httpResponse.statusCode, String(data: data, encoding: .utf8))
        }
        
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(T.self, from: data)
    }

    public func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T {
        let request = try await buildRequest(from: endpoint)
        return try await perform(request, allowRefreshRetry: true)
    }
    
    // 新增：支持直接传入路径的简易请求方法
    public func fetch<T: Decodable>(path: String, method: String = "GET") async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw APIError.invalidURL }
        await ensureFreshAccessTokenIfNeeded(forPath: url.path)

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request = await applyAccessToken(to: request)

        return try await perform(request, allowRefreshRetry: true)
    }

    // 新增：支持 JSON Body 的泛型请求方法 (用于 POST/PUT/PATCH)
    public func send<T: Encodable, U: Decodable>(path: String, method: String = "POST", body: T) async throws -> U {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw APIError.invalidURL }
        await ensureFreshAccessTokenIfNeeded(forPath: url.path)

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        request = await applyAccessToken(to: request)

        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            request.httpBody = try encoder.encode(body)
        } catch {
            throw APIError.decodingError(error) // 借用 decodingError 表示序列化失败
        }

        return try await perform(request, allowRefreshRetry: true)
    }

    private func perform<T: Decodable>(_ request: URLRequest, allowRefreshRetry: Bool) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        
        if httpResponse.statusCode == 401 {
            if allowRefreshRetry,
               await shouldAttemptRefresh(for: request),
               await tryRefreshSession() {
                var retriedRequest = request
                retriedRequest = await applyAccessToken(to: retriedRequest)
                return try await perform(retriedRequest, allowRefreshRetry: false)
            }

            await onUnauthorized?()
            throw APIError.unauthorized
        }

        if httpResponse.statusCode != 200 {
            let errorMsg = String(data: data, encoding: .utf8)
            throw APIError.serverError(httpResponse.statusCode, errorMsg)
        }
        
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(T.self, from: data)
    }

    private func buildRequest(from endpoint: Endpoint) async throws -> URLRequest {
        var components = URLComponents(url: baseURL.appendingPathComponent(endpoint.path), resolvingAgainstBaseURL: true)
        components?.queryItems = endpoint.queryItems
        
        guard let url = components?.url else { throw APIError.invalidURL }
        await ensureFreshAccessTokenIfNeeded(forPath: url.path)

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let customHeaders = endpoint.headers {
            for (header, value) in customHeaders {
                request.setValue(value, forHTTPHeaderField: header)
            }
        }

        request = await applyAccessToken(to: request)

        if let body = endpoint.body {
            request.httpBody = body
        }
        
        return request
    }

    private func applyAccessToken(to request: URLRequest) async -> URLRequest {
        var request = request
        if let token = await tokenProvider?() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    private func shouldAttemptRefresh(for request: URLRequest) async -> Bool {
        guard request.value(forHTTPHeaderField: "Authorization") != nil else { return false }
        guard let path = request.url?.path else { return false }
        guard path != "/api/v1/auth/login", path != "/api/v1/auth/refresh" else { return false }
        return await refreshTokenProvider?() != nil
    }

    private func ensureFreshAccessTokenIfNeeded(forPath path: String) async {
        guard path != "/api/v1/auth/login",
              path != "/api/v1/auth/refresh",
              path != "/api/v1/auth/passkeys/login/options",
              path != "/api/v1/auth/passkeys/login/verify" else {
            return
        }

        guard await refreshTokenProvider?() != nil else { return }

        let shouldRefresh: Bool
        if let expiry = await accessTokenExpiryProvider?() {
            shouldRefresh = expiry.timeIntervalSinceNow <= 60
        } else {
            shouldRefresh = await tokenProvider?() == nil
        }

        if shouldRefresh {
            _ = await tryRefreshSession()
        }
    }

    private func tryRefreshSession() async -> Bool {
        guard let refreshToken = await refreshTokenProvider?() else { return false }
        guard let url = URL(string: "/api/v1/auth/refresh", relativeTo: baseURL) else { return false }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        do {
            let body = RefreshTokenBody(refreshToken: refreshToken)
            request.httpBody = try JSONEncoder().encode(body)

            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                return false
            }

            let decoded = try JSONDecoder().decode(RefreshTokenResponse.self, from: data)
            await sessionUpdater?(decoded.accessToken, decoded.refreshToken, decoded.expiresIn)
            logger.debug("Session refreshed successfully.")
            return true
        } catch {
            logger.error("Session refresh failed: \(error.localizedDescription, privacy: .public)")
            return false
        }
    }
}

private struct RefreshTokenBody: Encodable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

private struct RefreshTokenResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    let expiresIn: Int?

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
    }
}
