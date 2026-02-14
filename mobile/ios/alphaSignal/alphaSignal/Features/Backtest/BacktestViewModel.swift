import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI

@Observable
class BacktestViewModel {
    var stats: BacktestStats?
    var isLoading = false
    var selectedWindow: String = "1h"
    var minScore: Int = 8
    var sentiment: String = "bearish"
    
    @MainActor
    func fetchStats() async {
        isLoading = true
        do {
            let path = "/api/v1/web/stats?window=\(selectedWindow)&min_score=\(minScore)&sentiment=\(sentiment)"
            let response: BacktestStats = try await APIClient.shared.fetch(path: path)
            withAnimation {
                self.stats = response
            }
        } catch {
            print("Failed to fetch V1 backtest stats: \(error)")
        }
        isLoading = false
    }
}
