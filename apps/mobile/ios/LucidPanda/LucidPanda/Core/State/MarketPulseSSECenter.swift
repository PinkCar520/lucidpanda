import Foundation
import OSLog
import AlphaCore
import AlphaData

/// 专用于行情快照（金价、DXY等）的实时推送中心
public actor MarketPulseSSECenter {
    public static let shared = MarketPulseSSECenter()
    private let logger = Logger(subsystem: "com.pineapple.LucidPanda", category: "MarketSSE")
    
    private var streamTask: Task<Void, Never>?
    private var subscribers: [UUID: AsyncStream<MarketPulseResponse>.Continuation] = [:]
    private var isConnected = false

    /// 订阅行情流
    func pulseStream() -> AsyncStream<MarketPulseResponse> {
        AsyncStream { continuation in
            let id = UUID()
            subscribers[id] = continuation
            
            Task { await self.reconfigureConnection() }
            
            continuation.onTermination = { @Sendable _ in
                Task { await self.removeSubscriber(id) }
            }
        }
    }

    private func removeSubscriber(_ id: UUID) {
        subscribers.removeValue(forKey: id)
        Task { await self.reconfigureConnection() }
    }

    private func reconfigureConnection() async {
        if subscribers.isEmpty {
            stopConnection()
        } else if !isConnected {
            await startConnection()
        }
    }

    private func startConnection() async {
        guard !subscribers.isEmpty && !isConnected else { return }
        isConnected = true
        
        streamTask = Task {
            while !Task.isCancelled {
                do {
                    let baseURL = await APIClient.shared.baseURL
                    let url = baseURL.appendingPathComponent("api/v1/mobile/market/pulse/stream")
                    let token = await MainActor.run { AuthTokenStore.accessToken() }
                    
                    let stream = await SSEResolver.shared.subscribe(url: url, token: token)
                    
                    logger.debug("📡 Market SSE Stream Connected")
                    
                    let decoder = JSONDecoder()
                    decoder.dateDecodingStrategy = .iso8601
                    
                    for try await payload in stream {
                        if Task.isCancelled { break }
                        if let data = payload.data(using: .utf8),
                           let pulse = try? decoder.decode(MarketPulseResponse.self, from: data) {
                            broadcast(pulse)
                        }
                    }
                } catch {
                    if Task.isCancelled { return }
                    logger.error("❌ Market SSE failed: \(error.localizedDescription, privacy: .public)")
                    try? await Task.sleep(nanoseconds: 5_000_000_000) // 5秒重连
                }
            }
        }
    }

    private func broadcast(_ pulse: MarketPulseResponse) {
        for sub in subscribers.values {
            sub.yield(pulse)
        }
    }

    private func stopConnection() {
        streamTask?.cancel()
        streamTask = nil
        isConnected = false
        logger.debug("⏹ Market SSE Stream Stopped")
    }
}
