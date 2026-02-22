// mobile/ios/alphaSignal/alphaSignal/Core/Sync/WatchlistSyncEngine.swift

import Foundation
import Combine
import Network
import UIKit
import AlphaData
import AlphaCore

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
            return "网络错误：\(error.localizedDescription)"
        case .serverError(let message):
            return "服务器错误：\(message)"
        case .syncConflict(let message):
            return "同步冲突：\(message)"
        case .remoteError(let message):
            return "远程错误：\(message)"
        case .notAuthenticated:
            return "未登录，请先登录"
        case .offline:
            return "离线状态，操作已加入队列"
        }
    }
}

// MARK: - SSE 事件

struct SSEEvent {
    let type: String
    let data: String
}

// MARK: - SSE 连接管理器

class SSEConnectionManager: NSObject {
    private var eventSource: URLSessionEventSource?
    private var eventHandler: ((SSEEvent) -> Void)?
    private var isConnected = false
    private var reconnectAttempts = 0
    private let maxReconnectAttempts = 5
    private let queue = DispatchQueue(label: "SSEConnectionManager")
    
    func connect(url: URL, onEvent: @escaping (SSEEvent) -> Void) {
        eventHandler = onEvent
        
        let request = URLRequest(url: url)
        eventSource = URLSessionEventSource(request: request)
        eventSource?.addEventHandler(self)
        eventSource?.resume()
        isConnected = true
        reconnectAttempts = 0
    }
    
    func disconnect() {
        eventSource?.cancel()
        eventSource = nil
        isConnected = false
    }
    
    func reconnect(url: URL, onEvent: @escaping (SSEEvent) -> Void) {
        guard reconnectAttempts < maxReconnectAttempts else {
            print("❌ SSE max reconnect attempts reached")
            return
        }
        
        reconnectAttempts += 1
        let delay = Double(reconnectAttempts) * 2.0 // 指数退避
        
        queue.asyncAfter(deadline: .now() + delay) { [weak self] in
            print("🔄 SSE reconnect attempt \(self?.reconnectAttempts ?? 0)/\(self?.maxReconnectAttempts ?? 5)")
            self?.connect(url: url, onEvent: onEvent)
        }
    }
}

extension SSEConnectionManager: URLSessionEventSourceEventHandler {
    func eventSource(_ eventSource: URLSessionEventSource, didReceiveEvent event: SSEEvent) {
        eventHandler?(event)
    }
    
    func eventSourceDidOpen(_ eventSource: URLSessionEventSource) {
        print("✅ SSE Connection opened")
        reconnectAttempts = 0
    }
    
    func eventSource(_ eventSource: URLSessionEventSource, didFailWithError error: Error) {
        print("❌ SSE Connection failed: \(error)")
        isConnected = false
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
        return isConnected
    }
    
    func addListener(_ callback: @escaping (Bool) -> Void) {
        listeners.append(callback)
        // 立即通知当前状态
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
    private let sseManager = SSEConnectionManager()
    private let networkMonitor = NetworkMonitor.shared
    private let deviceId = UIDevice.current.name
    
    // 同步配置
    private let syncInterval: TimeInterval = 30
    private var syncTimer: Timer?
    private var isAuthenticated = false
    
    func setup(lastSyncTime: Date? = nil) async {
        self.lastSyncTime = lastSyncTime
        
        // 监听网络状态
        networkMonitor.addListener { [weak self] connected in
            Task { @MainActor in
                self?.handleNetworkChange(connected)
            }
        }
        
        // 初始连接
        if networkMonitor.isNetworkAvailable() {
            await startSSEConnection()
        }
        
        startPeriodicSync()
    }
    
    func stop() {
        Task {
            sseManager.disconnect()
        }
        syncTimer?.invalidate()
    }
    
    // MARK: - 网络状态处理
    
    private func handleNetworkChange(_ connected: Bool) {
        if connected {
            connectionStatus = .connected
            isOffline = false
            
            // 网络恢复，同步待处理操作
            Task {
                await syncChanges()
            }
        } else {
            connectionStatus = .offline
            isOffline = true
        }
    }
    
    // MARK: - SSE 连接
    
    private func startSSEConnection() async {
        let url = URL(string: "/api/v2/watchlist/stream")!
        
        sseManager.connect(url: url) { [weak self] event in
            Task { @MainActor in
                self?.handleSSEEvent(event)
            }
        }
        
        connectionStatus = .connected
    }
    
    private func handleSSEEvent(_ event: SSEEvent) {
        switch event.type {
        case "watchlist.updated":
            // 收到远程更新，触发增量同步
            Task {
                await syncChanges()
            }
        case "error":
            if let data = event.data.data(using: .utf8),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let message = json["error"] as? String {
                syncError = WatchlistSyncError.remoteError(message: message)
            }
        default:
            break
        }
    }
    
    // MARK: - 周期性同步
    
    private func startPeriodicSync() {
        syncTimer = Timer.scheduledTimer(withTimeInterval: syncInterval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard self?.networkMonitor.isNetworkAvailable() == true else {
                    return
                }
                await self?.syncChanges()
            }
        }
    }
    
    // MARK: - 增量同步

    func syncChanges() async {
        guard !isSyncing else { return }

        // 检查网络
        if !networkMonitor.isNetworkAvailable() {
            syncError = WatchlistSyncError.offline
            return
        }

        isSyncing = true

        do {
            // 1. 上传待同步操作
            try await uploadPendingOperations()
            
            // 2. 拉取远程变更
            let since = lastSyncTime?.iso8601 ?? "1970-01-01T00:00:00Z"
            let path = "/api/v2/watchlist/sync?since=\(since)"
            let response: WatchlistItemsResponse = try await APIClient.shared.fetch(path: path)
            
            // 3. 合并数据
            await mergeRemoteData(response)
            
            // 4. 更新同步时间
            if let syncTimeStr = response.syncTime,
               let syncTime = ISO8601DateFormatter().date(from: syncTimeStr) {
                lastSyncTime = syncTime
            } else {
                lastSyncTime = Date()
            }
            
            syncError = nil
            
        } catch {
            syncError = error
            print("❌ Sync failed: \(error)")
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
        
        // 清除已成功同步的操作
        for result in response.results where result.success {
            await cacheManager.clearPendingOperations(for: result.fundCode)
        }
        
        // 记录失败的操作
        let failedOps = response.results.filter { !$0.success }
        if !failedOps.isEmpty {
            print("⚠️ Failed to sync \(failedOps.count) operations")
        }
    }
    
    // MARK: - 合并远程数据
    
    private func mergeRemoteData(_ response: WatchlistItemsResponse) async {
        // 保存分组
        await cacheManager.saveGroups(response.groups)
        
        // 保存自选项
        await cacheManager.saveItems(response.data)
        
        // 通知 ViewModel 刷新（通过 NotificationCenter）
        NotificationCenter.default.post(
            name: NSNotification.Name("WatchlistDidSync"),
            object: nil,
            userInfo: ["items": response.data, "groups": response.groups]
        )
        
        print("✅ Synced \(response.data.count) items and \(response.groups.count) groups")
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
        
        // 如果在线，立即同步
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
        
        // 如果在线，立即同步
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
        lastSyncTime = nil // 清除同步时间，强制全量同步
        await syncChanges()
    }
}

// MARK: - URLSessionEventSource (完整实现)

class URLSessionEventSource {
    private var task: URLSessionDataTask?
    private var eventHandler: URLSessionEventSourceEventHandler?
    private let session: URLSession
    
    init(request: URLRequest, session: URLSession = .shared) {
        self.session = session
        
        // 配置 SSE 请求
        var modifiedRequest = request
        modifiedRequest.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        modifiedRequest.setValue("keep-alive", forHTTPHeaderField: "Connection")
        
        task = session.dataTask(with: modifiedRequest) { [weak self] data, response, error in
            guard let self = self else { return }
            
            guard let data = data,
                  let lines = String(data: data, encoding: .utf8)?.components(separatedBy: "\n") else {
                if let error = error {
                    self.eventHandler?.eventSource(self, didFailWithError: error)
                }
                return
            }
            
            // 解析 SSE 格式
            var currentEvent = "message"
            var currentData = ""
            
            for line in lines {
                if line.hasPrefix("event:") {
                    currentEvent = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
                } else if line.hasPrefix("data:") {
                    currentData = String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
                } else if line.isEmpty && !currentData.isEmpty {
                    // 空行表示事件结束
                    let event = SSEEvent(type: currentEvent, data: currentData)
                    self.eventHandler?.eventSource(self, didReceiveEvent: event)
                    currentData = ""
                    currentEvent = "message"
                }
            }
            
            // 处理最后一个事件（如果没有空行结尾）
            if !currentData.isEmpty {
                let event = SSEEvent(type: currentEvent, data: currentData)
                self.eventHandler?.eventSource(self, didReceiveEvent: event)
            }
        }
    }
    
    func addEventHandler(_ handler: URLSessionEventSourceEventHandler) {
        eventHandler = handler
    }
    
    func resume() {
        task?.resume()
    }
    
    func cancel() {
        task?.cancel()
    }
}

protocol URLSessionEventSourceEventHandler: AnyObject {
    func eventSource(_ eventSource: URLSessionEventSource, didReceiveEvent event: SSEEvent)
    func eventSourceDidOpen(_ eventSource: URLSessionEventSource)
    func eventSource(_ eventSource: URLSessionEventSource, didFailWithError error: Error)
}

// MARK: - Date Extension

extension Date {
    var iso8601: String {
        ISO8601DateFormatter().string(from: self)
    }
}
