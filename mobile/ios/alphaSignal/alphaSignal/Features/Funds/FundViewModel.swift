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
            // 1. 获取用户的自选基金代码列表 (V1 BFF)
            let watchlistResponse: WatchlistDataResponse = try await APIClient.shared.fetch(path: "/api/v1/web/watchlist")
            let codes = watchlistResponse.data.map { $0.code }
            
            guard !codes.isEmpty else {
                self.watchlist = []
                isLoading = false
                return
            }
            
            // 2. 批量获取实时估值 (V1 BFF)
            let codesParam = codes.joined(separator: ",")
            let valuationResponse: BatchValuationResponse = try await APIClient.shared.fetch(
                path: "/api/v1/web/funds/batch-valuation?codes=\(codesParam)"
            )
            
            withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                self.watchlist = valuationResponse.data
            }
        } catch {
            print("❌ Failed to fetch V1 watchlist or valuations: \(error)")
        }
        isLoading = false
    }
    
    @MainActor
    func addFund(code: String, name: String) async {
        do {
            // 使用 V1 BFF 进行添加操作
            let item = WatchlistItemDTO(code: code, name: name)
            let _: SuccessResponse = try await APIClient.shared.send(
                path: "/api/v1/web/watchlist",
                body: item
            )
            await fetchWatchlist()
        } catch {
            print("❌ Failed to add fund via V1: \(error)")
        }
    }
    
    @MainActor
    func deleteFund(code: String) async {
        do {
            // 使用 V1 BFF 进行删除操作
            let _: SuccessResponse = try await APIClient.shared.fetch(
                path: "/api/v1/web/watchlist/\(code)",
                method: "DELETE"
            )
            await fetchWatchlist()
        } catch {
            print("❌ Failed to delete fund via V1: \(error)")
        }
    }
}

// 补充 DTO 定义以匹配 V1 BFF
struct WatchlistDataResponse: Codable {
    let data: [WatchlistItemDTO]
}

struct WatchlistItemDTO: Codable {
    let code: String
    let name: String
}

struct BatchValuationResponse: Codable {
    let data: [FundValuation]
}

struct SuccessResponse: Codable {
    let success: Bool
}
