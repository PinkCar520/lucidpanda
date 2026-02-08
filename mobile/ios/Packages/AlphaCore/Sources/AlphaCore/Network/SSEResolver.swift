// mobile/ios/Packages/AlphaCore/Sources/AlphaCore/Network/SSEResolver.swift
import Foundation
import OSLog

public actor SSEResolver {
    public static let shared = SSEResolver()
    private let logger = Logger(subsystem: "com.pincar.alphasignal", category: "SSE")
    private var session: URLSession?
    
    private init() {}
    
    public func subscribe(url: URL, token: String?) -> AsyncThrowingStream<String, Error> {
        return AsyncThrowingStream { continuation in
            let config = URLSessionConfiguration.default
            config.timeoutIntervalForRequest = 3600 // 长连接超时设置
            config.timeoutIntervalForResource = 3600
            
            let session = URLSession(configuration: config)
            self.session = session
            
            var request = URLRequest(url: url)
            if let token = token {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
            request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
            request.cachePolicy = .reloadIgnoringLocalAndRemoteCacheData
            
            Task {
                do {
                    let (bytes, response) = try await session.bytes(for: request)
                    
                    guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                        logger.error("❌ SSE Connection failed")
                        continuation.finish(throwing: APIError.invalidResponse)
                        return
                    }
                    
                    logger.debug("✅ SSE Stream connected")
                    
                    for try await line in bytes.lines {
                        if line.hasPrefix("data: ") {
                            let data = String(line.dropFirst(6))
                            continuation.yield(data)
                        }
                    }
                    
                    continuation.finish()
                } catch {
                    logger.error("❌ SSE Stream error: \(error.localizedDescription)")
                    continuation.finish(throwing: error)
                }
            }
            
            continuation.onTermination = { @Sendable _ in
                Task { await self.stop() }
            }
        }
    }
    
    public func stop() {
        session?.invalidateAndCancel()
        session = nil
        logger.debug("⏹ SSE Stream stopped")
    }
}
