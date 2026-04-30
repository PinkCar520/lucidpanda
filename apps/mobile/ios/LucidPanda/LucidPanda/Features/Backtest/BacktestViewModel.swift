import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI
import OSLog

@MainActor
@Observable
class BacktestViewModel {
    private let logger = AppLog.dashboard
    var stats: BacktestStats?
    var isLoading = false
    var errorMessage: String?
    
    // --- Signal Filter Config (Existing) ---
    var selectedWindow: String = "1h"
    var minScore: Int = 8
    var sentiment: String = "bearish"
    
    // --- Simulation Config (New) ---
    var strategyType: StrategyType = .meanReversion
    var startDate: Date = Calendar.current.date(byAdding: .month, value: -6, to: Date()) ?? Date()
    var endDate: Date = Date()
    var initialCapital: Double = 10000
    
    enum StrategyType: String, CaseIterable, Identifiable {
        case meanReversion = "mean-reversion"
        case momentum = "momentum"
        case breakout = "breakout"
        case arbitrage = "arbitrage"
        
        var id: String { rawValue }
        var localizedName: String {
            switch self {
            case .meanReversion: return String(localized: "backtest.strategy.mean_reversion")
            case .momentum: return String(localized: "backtest.strategy.momentum")
            case .breakout: return String(localized: "backtest.strategy.breakout")
            case .arbitrage: return String(localized: "backtest.strategy.arbitrage")
            }
        }
    }
    
    private var pendingRefreshTask: Task<Void, Never>?
    private var inFlightFetchTask: Task<Void, Never>?
    
    enum RefreshTrigger {
        case immediate
        case debounced
    }
    
    func applySavedConfiguration(window: String, minScore: Int, sentiment: String) {
        selectedWindow = window
        self.minScore = minScore
        self.sentiment = sentiment
    }
    
    func fetchStats() async {
        inFlightFetchTask?.cancel()
        
        let fetchTask = Task { @MainActor in
            isLoading = true
            errorMessage = nil
            defer { isLoading = false }
            
            do {
                let isoFormatter = ISO8601DateFormatter()
                let startStr = isoFormatter.string(from: startDate)
                let endStr = isoFormatter.string(from: endDate)
                
                var path = "/api/v1/web/stats?window=\(selectedWindow)&min_score=\(minScore)&sentiment=\(sentiment)"
                path += "&strategy_type=\(strategyType.rawValue)"
                path += "&start_date=\(startStr.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
                path += "&end_date=\(endStr.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
                path += "&initial_capital=\(initialCapital)"
                
                let response: BacktestStats = try await APIClient.shared.fetch(path: path)
                try Task.checkCancellation()
                withAnimation {
                    self.stats = response
                }
            } catch is CancellationError {
                return
            } catch {
                errorMessage = NSLocalizedString("error.network.generic", comment: "")
                logger.error("Failed to fetch V1 backtest stats: \(error.localizedDescription, privacy: .public)")
            }
        }
        
        inFlightFetchTask = fetchTask
        await fetchTask.value
    }
    
    func scheduleRefresh(_ trigger: RefreshTrigger) {
        pendingRefreshTask?.cancel()
        
        pendingRefreshTask = Task { @MainActor in
            if trigger == .debounced {
                try? await Task.sleep(nanoseconds: 400_000_000)
            }
            guard !Task.isCancelled else { return }
            await fetchStats()
        }
    }
    
    func fetchIntelligenceDetail(id: Int) async throws -> IntelligenceItem {
        let path = "/api/v1/web/intelligence/\(id)"
        return try await APIClient.shared.fetch(path: path)
    }
    
}
