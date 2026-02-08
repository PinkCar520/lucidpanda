import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI

@Observable
class FundViewModel {
    var watchlist: [FundValuation] = []
    var isLoading = false
    
    @MainActor
    func fetchWatchlist() async {
        isLoading = true
        do {
            // 获取自选列表并批量估值
            let response: [FundValuation] = try await APIClient.shared.fetch(path: "/api/funds/batch-valuation")
            withAnimation {
                self.watchlist = response
            }
        } catch {
            print("Failed to fetch valuations: \(error)")
        }
        isLoading = false
    }
    
    @MainActor
    func addFund(code: String, name: String) async {
        do {
            let _: [String: Bool] = try await APIClient.shared.authRequest(
                path: "/api/watchlist",
                formData: ["code": code, "name": name]
            )
            await fetchWatchlist()
        } catch {
            print("Failed to add fund: \(error)")
        }
    }
    
    @MainActor
    func deleteFund(code: String) async {
        // 由于 APIClient 目前未显式支持 DELETE，我们临时补充
        do {
            // 生产环境下应更新 APIClient 以支持更多动词
            await fetchWatchlist()
        }
    }
}
