import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI

@MainActor
@Observable
class BacktestViewModel {
    var stats: BacktestStats?
    var isLoading = false
    var selectedWindow: String = "1h"
    var minScore: Int = 8
    var sentiment: String = "bearish"
    var errorMessage: String?
    
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
                let path = "/api/v1/web/stats?window=\(selectedWindow)&min_score=\(minScore)&sentiment=\(sentiment)"
                let response: BacktestStats = try await APIClient.shared.fetch(path: path)
                try Task.checkCancellation()
                withAnimation {
                    self.stats = response
                }
            } catch is CancellationError {
                return
            } catch {
                errorMessage = NSLocalizedString("error.network.generic", comment: "")
                print("Failed to fetch V1 backtest stats: \(error)")
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
