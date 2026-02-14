import Foundation
import OSLog

public actor APIClient {
    public static let shared = APIClient()
    private let session = URLSession.shared
    private let logger = Logger(subsystem: "com.pincar.alphasignal", category: "APIClient")
    
    // 允许外部注入 Token 获取逻辑，避免循环依赖
    private var tokenProvider: (() async -> String?)?
    private var onUnauthorized: (() async -> Void)?
    
    public func setTokenProvider(_ provider: @escaping () async -> String?) {
        self.tokenProvider = provider
    }
    
    public func setOnUnauthorized(_ handler: @escaping () async -> Void) {
        self.onUnauthorized = handler
    }
    
    #if DEBUG
    private let baseURL = URL(string: "http://127.0.0.1:8001")!
    #else
    private let baseURL = URL(string: "https://your-api.com")!
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
        return try await perform(request)
    }
    
    // 新增：支持直接传入路径的简易请求方法
    public func fetch<T: Decodable>(path: String, method: String = "GET") async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = await tokenProvider?() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        return try await perform(request)
    }

    // 新增：支持 JSON Body 的泛型请求方法 (用于 POST/PUT/PATCH)
    public func send<T: Encodable, U: Decodable>(path: String, method: String = "POST", body: T) async throws -> U {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = await tokenProvider?() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            request.httpBody = try encoder.encode(body)
        } catch {
            throw APIError.decodingError(error) // 借用 decodingError 表示序列化失败
        }
        
        return try await perform(request)
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        
        if httpResponse.statusCode == 401 { 
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
        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = await tokenProvider?() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        if let body = endpoint.body {
            request.httpBody = body
        }
        
        return request
    }
}