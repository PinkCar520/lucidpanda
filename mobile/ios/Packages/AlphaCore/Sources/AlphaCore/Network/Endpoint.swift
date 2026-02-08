// mobile/ios/Packages/AlphaCore/Sources/AlphaCore/Network/APIError.swift
import Foundation

public enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case decodingError(Error)
    case serverError(Int, String?)
    case unauthorized
    case networkError(Error)
    case unknown
    
    public var errorDescription: String? {
        switch self {
        case .invalidURL: return "The request URL is invalid."
        case .invalidResponse: return "The server returned an invalid response."
        case .decodingError(let error): return "Failed to decode response: \(error.localizedDescription)"
        case .serverError(let code, let msg): return "Server error (\(code)): \(msg ?? "No message")"
        case .unauthorized: return "Session expired or unauthorized access."
        case .networkError(let error): return "Network connection issue: \(error.localizedDescription)"
        case .unknown: return "An unknown error occurred."
        }
    }
}

// mobile/ios/Packages/AlphaCore/Sources/AlphaCore/Network/Endpoint.swift
import Foundation

public enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case delete = "DELETE"
    case patch = "PATCH"
}

public protocol Endpoint {
    var path: String { get }
    var method: HTTPMethod { get }
    var headers: [String: String]? { get }
    var queryItems: [URLQueryItem]? { get }
    var body: Data? { get }
}

extension Endpoint {
    public var headers: [String: String]? { nil }
    public var queryItems: [URLQueryItem]? { nil }
    public var body: Data? { nil }
}
