// mobile/ios/Packages/AlphaCore/Sources/AlphaCore/Network/SSEResolver.swift
import Foundation
import OSLog

public actor SSEResolver {
    public static let shared = SSEResolver()
    private let logger = Logger(subsystem: "com.pincar.alphasignal", category: "SSE")
    private var activeSessions: [UUID: URLSession] = [:]
    
    private init() {}

    private func isCancelledError(_ error: Error) -> Bool {
        if error is CancellationError { return true }
        if let urlError = error as? URLError, urlError.code == .cancelled { return true }
        let nsError = error as NSError
        return nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorCancelled
    }
    
    public func subscribe(url: URL, token: String?) -> AsyncThrowingStream<String, Error> {
        return AsyncThrowingStream { continuation in
            let streamID = UUID()
            let config = URLSessionConfiguration.default
            config.timeoutIntervalForRequest = 3600 // 长连接超时设置
            config.timeoutIntervalForResource = 3600
            
            let session = URLSession(configuration: config)
            Task { await self.registerSession(session, for: streamID) }
            
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
                    if await self.isCancelledError(error) {
                        continuation.finish()
                        await self.stop(streamID: streamID)
                        return
                    }
                    logger.error("❌ SSE Stream error: \(error.localizedDescription)")
                    await self.stop(streamID: streamID)
                    continuation.finish(throwing: error)
                }
            }
            
            continuation.onTermination = { @Sendable _ in
                Task { await self.stop(streamID: streamID) }
            }
        }
    }

    private func registerSession(_ session: URLSession, for streamID: UUID) {
        activeSessions[streamID] = session
    }

    private func stop(streamID: UUID) {
        guard let session = activeSessions.removeValue(forKey: streamID) else { return }
        session.invalidateAndCancel()
        logger.debug("⏹ SSE Stream stopped")
    }
    
    public func stop() {
        guard !activeSessions.isEmpty else { return }
        for (_, session) in activeSessions {
            session.invalidateAndCancel()
        }
        activeSessions.removeAll()
        logger.debug("⏹ SSE Stream stopped")
    }
}
