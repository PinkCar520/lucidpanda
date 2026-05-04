import Foundation
import OSLog
import AlphaCore
import AlphaData

actor FundValuationSSECenter {
    static let shared = FundValuationSSECenter()

    private struct Subscriber {
        var codes: Set<String>
        var continuation: AsyncStream<FundValuation>.Continuation?
    }

    private let logger = Logger(subsystem: "com.pineapple.LucidPanda", category: "FundValuationSSE")
    private var subscribers: [String: Subscriber] = [:]
    private var streamTask: Task<Void, Never>?
    private var activeCodes: Set<String> = []
    private var reconnectAttempt: Int = 0

    private init() {}

    func events(for subscriberID: String) -> AsyncStream<FundValuation> {
        AsyncStream { continuation in
            var subscriber = subscribers[subscriberID] ?? Subscriber(codes: [], continuation: nil)
            subscriber.continuation = continuation
            subscribers[subscriberID] = subscriber

            Task { await self.reconfigureStreamIfNeeded() }

            continuation.onTermination = { @Sendable _ in
                Task { await self.removeSubscriber(subscriberID) }
            }
        }
    }

    func setCodes(_ codes: Set<String>, for subscriberID: String) {
        var subscriber = subscribers[subscriberID] ?? Subscriber(codes: [], continuation: nil)
        subscriber.codes = codes
        subscribers[subscriberID] = subscriber
        Task { await self.reconfigureStreamIfNeeded() }
    }

    private func removeSubscriber(_ subscriberID: String) {
        subscribers.removeValue(forKey: subscriberID)
        Task { await self.reconfigureStreamIfNeeded() }
    }

    private func desiredCodes() -> Set<String> {
        subscribers.values.reduce(into: Set<String>()) { partial, sub in
            partial.formUnion(sub.codes)
        }
    }

    private func reconfigureStreamIfNeeded() async {
        let desired = desiredCodes()
        guard desired != activeCodes else { return }

        streamTask?.cancel()
        streamTask = nil
        activeCodes = desired
        reconnectAttempt = 0

        guard !desired.isEmpty else { return }

        streamTask = Task { [weak self] in
            guard let self else { return }
            await self.runStreamLoop()
        }
    }

    private func runStreamLoop() async {
        while !Task.isCancelled {
            let codes = activeCodes
            guard !codes.isEmpty else { return }

            do {
                try await consumeSSE(for: codes)
                if Task.isCancelled { return }
                reconnectAttempt = 0
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            } catch {
                if Task.isCancelled { return }
                reconnectAttempt += 1
                logger.error("Fund SSE stream failed: \(error.localizedDescription, privacy: .public)")
                await pollFallback(for: codes)
                let delay = min(30, max(2, reconnectAttempt * 2))
                try? await Task.sleep(nanoseconds: UInt64(delay) * 1_000_000_000)
            }
        }
    }

    private func consumeSSE(for codes: Set<String>) async throws {
        let sortedCodes = codes.sorted()
        guard !sortedCodes.isEmpty else { return }

        let baseURL = APIClient.shared.baseURL
        var components = URLComponents(url: baseURL.appendingPathComponent("api/v1/web/funds/stream"), resolvingAgainstBaseURL: false)
        components?.queryItems = [URLQueryItem(name: "codes", value: sortedCodes.joined(separator: ","))]
        guard let url = components?.url else { throw APIError.invalidURL }

        let token = await MainActor.run { AuthTokenStore.accessToken() }
        let stream = await SSEResolver.shared.subscribe(url: url, token: token)

        for try await payload in stream {
            if Task.isCancelled { return }
            let updates = decodeUpdates(from: payload)
            if updates.isEmpty { continue }
            for update in updates {
                broadcast(update)
            }
        }
    }

    private func pollFallback(for codes: Set<String>) async {
        guard !codes.isEmpty else { return }
        let sortedCodes = codes.sorted()
        let path = "/api/v1/web/funds/batch-valuation?codes=\(sortedCodes.joined(separator: ","))"

        do {
            let response: SSEBatchValuationResponse = try await APIClient.shared.fetch(path: path)
            for valuation in response.data {
                broadcast(valuation)
            }
        } catch {
            logger.error("Fund SSE fallback poll failed: \(error.localizedDescription, privacy: .public)")
        }
    }

    private func broadcast(_ valuation: FundValuation) {
        for (_, subscriber) in subscribers where subscriber.codes.contains(valuation.fundCode) {
            subscriber.continuation?.yield(valuation)
        }
    }

    private func decodeUpdates(from payload: String) -> [FundValuation] {
        guard let data = payload.data(using: .utf8) else { return [] }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        if let single = try? decoder.decode(FundValuation.self, from: data) {
            return [single]
        }

        guard
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let wrapped = object["data"]
        else {
            return []
        }

        if let dict = wrapped as? [String: Any],
           let wrappedData = try? JSONSerialization.data(withJSONObject: dict),
           let one = try? decoder.decode(FundValuation.self, from: wrappedData) {
            return [one]
        }

        if let array = wrapped as? [[String: Any]],
           let wrappedData = try? JSONSerialization.data(withJSONObject: array),
           let many = try? decoder.decode([FundValuation].self, from: wrappedData) {
            return many
        }

        return []
    }
}

private struct SSEBatchValuationResponse: Decodable {
    let data: [FundValuation]
}
