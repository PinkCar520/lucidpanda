// mobile/ios/LucidPanda/LucidPanda/Features/Market/MarketPulseViewModel.swift
import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI

@Observable
public class MarketPulseViewModel {
    private let apiClient = APIClient.shared
    private let pulseCacheKey = "com.pincar.cache.market_pulse"
    
    public private(set) var pulseData: MarketPulseResponse?
    public private(set) var timechainData: MarketTimechainResponse?
    public var isLoading = false
    public var isTimechainLoading = false
    public var lastUpdated: Date?
    
    private let refreshInterval: TimeInterval = 60 // 1 minute refresh
    private var refreshTimer: Timer?
    private var sseTask: Task<Void, Never>?
    
    public init() {
        loadPulseFromCache()
    }
    
    private func loadPulseFromCache() {
        if let data = UserDefaults.standard.data(forKey: pulseCacheKey),
           let cached = try? JSONDecoder().decode(MarketPulseResponse.self, from: data) {
            self.pulseData = cached
        }
    }
    
    private func savePulseToCache(_ pulse: MarketPulseResponse) {
        if let data = try? JSONEncoder().encode(pulse) {
            UserDefaults.standard.set(data, forKey: pulseCacheKey)
        }
    }
    
    @MainActor
    public func start() async {
        guard !isLoading else { return }
        
        // 1. 获取初始快照 (此处内部会自动调用 savePulseToCache)
        await fetchPulse()
        
        // 2. 建立 SSE 长连接流
        sseTask?.cancel()
        sseTask = Task {
            let stream = await MarketPulseSSECenter.shared.pulseStream()
            for await newPulse in stream {
                // 使用弹簧动画确保 UI 丝滑更新
                withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                    self.pulseData = newPulse
                    self.lastUpdated = Date()
                    self.savePulseToCache(newPulse)
                }
            }
        }
        
        // 3. 开启轮询作为兜底 (Fallback)
        startAutoRefresh()
    }
    
    @MainActor
    public func fetchPulse() async {
        isLoading = true
        do {
            let data: MarketPulseResponse = try await apiClient.fetch(path: "/api/v1/mobile/market/pulse")
            savePulseToCache(data)
            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                self.pulseData = data
                self.lastUpdated = Date()
            }
        } catch {
            print("Failed to fetch market pulse: \(error)")
        }
        isLoading = false
    }

    @MainActor
    public func fetchTimechain() async {
        guard !isTimechainLoading else { return }
        isTimechainLoading = true
        
        let savedLanguage = UserDefaults.standard.string(forKey: "appLanguage") ?? "system"
        let languageCode = savedLanguage != "system" ? savedLanguage.lowercased() : (Bundle.main.preferredLocalizations.first?.lowercased() ?? "en")
        let language = languageCode.contains("zh") ? "zh" : "en"
        
        do {
            let data: MarketTimechainResponse = try await apiClient.fetch(path: "/api/v1/mobile/market/pulse/timechain?lang=\(language)")
            withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
                self.timechainData = data
            }
        } catch {
            print("Failed to fetch timechain: \(error)")
        }
        isTimechainLoading = false
    }
    
    private func startAutoRefresh() {
        refreshTimer?.invalidate()
        refreshTimer = Timer.scheduledTimer(withTimeInterval: refreshInterval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.fetchPulse()
            }
        }
    }
    
    public func stop() {
        refreshTimer?.invalidate()
        refreshTimer = nil
        sseTask?.cancel()
        sseTask = nil
    }
}
