// mobile/ios/LucidPanda/LucidPanda/Core/Sync/WatchlistSyncEngine.swift

import Foundation
import Combine
import Network
import AlphaData
import AlphaCore
import OSLog

// MARK: - 同步错误

enum WatchlistSyncError: LocalizedError {
    case networkError(Error)
    case serverError(String)
    case syncConflict(String)
    case remoteError(message: String)
    case notAuthenticated
    case offline
    
    var errorDescription: String? {
        switch self {
        case .networkError(let error):
            return String(format: NSLocalizedString("sync.error.network %@", comment: ""), error.localizedDescription)
        case .serverError(let message):
            return String(format: NSLocalizedString("sync.error.server %@", comment: ""), message)
        case .syncConflict(let message):
            return String(format: NSLocalizedString("sync.error.conflict %@", comment: ""), message)
        case .remoteError(let message):
            return String(format: NSLocalizedString("sync.error.remote %@", comment: ""), message)
        case .notAuthenticated:
            return NSLocalizedString("sync.error.not_authenticated", comment: "")
        case .offline:
            return NSLocalizedString("sync.error.offline", comment: "")
        }
    }
}

// MARK: - 网络状态监控

class NetworkMonitor: ObservableObject {
    static let shared = NetworkMonitor()
    
    private let monitor = NWPathMonitor()
    @Published var isConnected: Bool = false
    private var listeners: [(Bool) -> Void] = []
    
    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            let wasConnected = self?.isConnected ?? false
            self?.isConnected = path.status == .satisfied
            
            if wasConnected != self?.isConnected {
                self?.notifyListeners()
            }
        }
        monitor.start(queue: DispatchQueue(label: "NetworkMonitor"))
    }
    
    func isNetworkAvailable() -> Bool {
        isConnected
    }
    
    func addListener(_ callback: @escaping (Bool) -> Void) {
        listeners.append(callback)
        callback(isConnected)
    }
    
    private func notifyListeners() {
        for listener in listeners {
            listener(isConnected)
        }
    }
}

// MARK: - 同步引擎

@MainActor
class WatchlistSyncEngine: ObservableObject {
    static let shared = WatchlistSyncEngine()
    private let logger = AppLog.watchlist
    
    @Published var isSyncing = false
    @Published var lastSyncTime: Date?
    @Published var syncError: Error?
    @Published var connectionStatus: ConnectionStatus = .disconnected
    @Published var isOffline = false
    
    enum ConnectionStatus {
        case connected
        case disconnected
        case reconnecting
        case offline
    }
    
    private let cacheManager = WatchlistCacheManager.shared
    private let networkMonitor = NetworkMonitor.shared
    
    // 同步配置
    private let syncInterval: TimeInterval = 30
    private var syncTimer: Timer?
    private var isSetupComplete = false
    
    // SSE 生命周期
    private var streamTask: Task<Void, Never>?
    private var reconnectTask: Task<Void, Never>?
    private var reconnectAttempt = 0
    private let maxReconnectAttempts = 5
    
    func setup(lastSyncTime: Date? = nil) async {
        if isSetupComplete { return }
        isSetupComplete = true
        self.lastSyncTime = lastSyncTime
        
        networkMonitor.addListener { [weak self] connected in
            Task { @MainActor in
                self?.handleNetworkChange(connected)
            }
        }
        
        if networkMonitor.isNetworkAvailable() {
            startSSEConnection()
        }
        
        startPeriodicSync()
    }
    
    func stop() {
        reconnectTask?.cancel()
        reconnectTask = nil
        streamTask?.cancel()
        streamTask = nil
        
        syncTimer?.invalidate()
        syncTimer = nil
        
        connectionStatus = .disconnected
        isSyncing = false
        isSetupComplete = false
        reconnectAttempt = 0
    }
    
    // MARK: - 网络状态处理
    
    private func handleNetworkChange(_ connected: Bool) {
        if connected {
            isOffline = false
            startSSEConnection()
            Task { await syncChanges() }
        } else {
            isOffline = true
            connectionStatus = .offline
            streamTask?.cancel()
            streamTask = nil
        }
    }
    
    // MARK: - SSE 连接
    
    private func startSSEConnection() {
        guard networkMonitor.isNetworkAvailable() else {
            connectionStatus = .offline
            return
        }
        guard AuthTokenStore.accessToken() != nil else {
            connectionStatus = .disconnected
            return
        }
        
        streamTask?.cancel()
        streamTask = nil
        reconnectTask?.cancel()
        reconnectTask = nil
        
        connectionStatus = reconnectAttempt == 0 ? .disconnected : .reconnecting
        
        streamTask = Task { [weak self] in
            guard let self else { return }
            
            do {
                let baseURL = APIClient.shared.baseURL
                let streamURL = baseURL.appendingPathComponent("api/v2/watchlist/stream")
                let token = AuthTokenStore.accessToken()
                let stream = await SSEResolver.shared.subscribe(url: streamURL, token: token)
                
                self.connectionStatus = .connected
                self.reconnectAttempt = 0
                
                for try await data in stream {
                    if Task.isCancelled { return }
                    self.handleSSEPayload(data)
                }
                
                if Task.isCancelled { return }
                self.scheduleReconnect()
            } catch {
                if Task.isCancelled || self.isCancelledError(error) { return }
                self.syncError = WatchlistSyncError.networkError(error)
                self.scheduleReconnect()
            }
        }
    }
    
    private func scheduleReconnect() {
        guard !Task.isCancelled else { return }
        guard networkMonitor.isNetworkAvailable() else {
            connectionStatus = .offline
            return
        }
        guard reconnectAttempt < maxReconnectAttempts else {
            connectionStatus = .disconnected
            return
        }
        
        reconnectAttempt += 1
        connectionStatus = .reconnecting
        
        let delay = UInt64(reconnectAttempt * 2) * 1_000_000_000
        reconnectTask?.cancel()
        reconnectTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: delay)
            guard !Task.isCancelled else { return }
            await MainActor.run {
                self?.startSSEConnection()
            }
        }
    }
    
    private func handleSSEPayload(_ payload: String) {
        // `SSEResolver` returns `data:` lines only.
        // Handle both payload shapes:
        // 1) {"event":"watchlist.updated","data":{...}}
        // 2) {"type":"watchlist.updated", ...}
        guard let data = payload.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }
        
        let event = (json["event"] as? String) ?? (json["type"] as? String)
        
        switch event {
        case "watchlist.updated":
            Task { await syncChanges() }
        case "error":
            if let message = json["error"] as? String {
                syncError = WatchlistSyncError.remoteError(message: message)
            } else if let nested = json["data"] as? [String: Any],
                      let message = nested["error"] as? String {
                syncError = WatchlistSyncError.remoteError(message: message)
            }
        default:
            break
        }
    }
    
    private func isCancelledError(_ error: Error) -> Bool {
        if error is CancellationError { return true }
        if let urlError = error as? URLError, urlError.code == .cancelled { return true }
        let nsError = error as NSError
        return nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorCancelled
    }
    
    // MARK: - 周期性同步
    
    private func startPeriodicSync() {
        syncTimer = Timer.scheduledTimer(withTimeInterval: syncInterval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard self?.networkMonitor.isNetworkAvailable() == true else { return }
                await self?.syncChanges()
            }
        }
    }
    
    // MARK: - 增量同步
    
    func syncChanges() async {
        guard !isSyncing else { return }
        guard AuthTokenStore.accessToken() != nil || AuthTokenStore.refreshToken() != nil else {
            syncError = WatchlistSyncError.notAuthenticated
            return
        }
        
        if !networkMonitor.isNetworkAvailable() {
            syncError = WatchlistSyncError.offline
            return
        }
        
        isSyncing = true
        
        do {
            try await uploadPendingOperations()
            
            let since = lastSyncTime?.iso8601 ?? "1970-01-01T00:00:00Z"
            let path = "/api/v2/watchlist/sync?since=\(since)"
            let response: WatchlistItemsResponse = try await APIClient.shared.fetch(path: path)
            
            await mergeRemoteData(response)
            
            if let syncTimeStr = response.syncTime,
               let syncTime = ISO8601DateFormatter().date(from: syncTimeStr) {
                lastSyncTime = syncTime
            } else {
                lastSyncTime = Date()
            }
            
            syncError = nil
        } catch {
            syncError = error
            logger.error("Sync failed: \(error.localizedDescription, privacy: .public)")
        }
        
        isSyncing = false
    }
    
    // MARK: - 上传待同步操作
    
    private func uploadPendingOperations() async throws {
        let pendingOps = await cacheManager.getPendingOperations()
        guard !pendingOps.isEmpty else { return }
        
        let request = SyncRequest(
            operations: pendingOps,
            lastSyncTime: lastSyncTime
        )
        
        let response: SyncResponse = try await APIClient.shared.send(
            path: "/api/v2/watchlist/sync",
            method: "POST",
            body: request
        )
        
        for result in response.results where result.success {
            await cacheManager.clearPendingOperations(for: result.fundCode)
        }
        
        let failedOps = response.results.filter { !$0.success }
        if !failedOps.isEmpty {
            logger.warning("Failed to sync \(failedOps.count, privacy: .public) operations")
        }
    }
    
    // MARK: - 合并远程数据
    
    private func mergeRemoteData(_ response: WatchlistItemsResponse) async {
        await cacheManager.saveGroups(response.groups)
        await cacheManager.saveItems(response.data)
        
        NotificationCenter.default.post(
            name: NSNotification.Name("WatchlistDidSync"),
            object: nil,
            userInfo: ["items": response.data, "groups": response.groups]
        )
        
        logger.info("Synced \(response.data.count, privacy: .public) items and \(response.groups.count, privacy: .public) groups")
    }
    
    // MARK: - 队列操作
    
    func enqueueAdd(fundCode: String, fundName: String, groupId: String? = nil) async {
        let operation = PendingOperation(
            operationType: .add,
            fundCode: fundCode,
            fundName: fundName,
            groupId: groupId
        )
        await cacheManager.addPendingOperation(operation)
        
        if networkMonitor.isNetworkAvailable() {
            await syncChanges()
        }
    }
    
    func enqueueRemove(fundCode: String) async {
        let operation = PendingOperation(
            operationType: .remove,
            fundCode: fundCode
        )
        await cacheManager.addPendingOperation(operation)
        
        if networkMonitor.isNetworkAvailable() {
            await syncChanges()
        }
    }
    
    func enqueueMove(fundCode: String, groupId: String?) async {
        let operation = PendingOperation(
            operationType: .moveGroup,
            fundCode: fundCode,
            groupId: groupId
        )
        await cacheManager.addPendingOperation(operation)
        
        if networkMonitor.isNetworkAvailable() {
            await syncChanges()
        }
    }
    
    func enqueueReorder(fundCode: String, sortIndex: Int) async {
        let operation = PendingOperation(
            operationType: .reorder,
            fundCode: fundCode,
            sortIndex: sortIndex
        )
        await cacheManager.addPendingOperation(operation)
        
        if networkMonitor.isNetworkAvailable() {
            await syncChanges()
        }
    }
    
    // MARK: - 强制刷新
    
    func forceSync() async {
        lastSyncTime = nil
        await syncChanges()
    }
}

// MARK: - Date Extension

extension Date {
    var iso8601: String {
        ISO8601DateFormatter().string(from: self)
    }
}
