// mobile/ios/LucidPanda/LucidPanda/Features/Market/MarketPulseViewModel.swift
import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI

@Observable
public class MarketPulseViewModel {
    private let apiClient = APIClient.shared
    
    public private(set) var pulseData: MarketPulseResponse?
    public var isLoading = false
    public var lastUpdated: Date?
    
    private let refreshInterval: TimeInterval = 60 // 1 minute refresh
    private var refreshTimer: Timer?
    
    public init() {}
    
    @MainActor
    public func start() async {
        guard !isLoading else { return }
        await fetchPulse()
        startAutoRefresh()
    }
    
    @MainActor
    public func fetchPulse() async {
        isLoading = true
        do {
            let data: MarketPulseResponse = try await apiClient.fetch(path: "/api/v1/mobile/market/pulse")
            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                self.pulseData = data
                self.lastUpdated = Date()
            }
        } catch {
            print("Failed to fetch market pulse: \(error)")
        }
        isLoading = false
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
    }
}
