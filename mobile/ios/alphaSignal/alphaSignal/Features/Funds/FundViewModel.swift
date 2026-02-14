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
            // 1. 获取用户的自选基金代码列表
            // 对齐 sse_server.py: @app.get("/api/watchlist")
            let watchlistResponse: WatchlistDataResponse = try await APIClient.shared.fetch(path: "/api/watchlist")
            let codes = watchlistResponse.data.map { $0.code }
            
            guard !codes.isEmpty else {
                self.watchlist = []
                isLoading = false
                return
            }
            
            // 2. 批量获取实时估值
            // 对齐 sse_server.py: @app.get("/api/funds/batch-valuation")
            let codesParam = codes.joined(separator: ",")
            let valuationResponse: BatchValuationResponse = try await APIClient.shared.fetch(
                path: "/api/funds/batch-valuation?codes=\(codesParam)"
            )
            
            withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                self.watchlist = valuationResponse.data
            }
        } catch {
            print("❌ Failed to fetch watchlist or valuations: \(error)")
        }
        isLoading = false
    }
    
    @MainActor
    func addFund(code: String, name: String) async {
        do {
            // 对齐 sse_server.py: @app.post("/api/watchlist")
            // 使用新定义的 send 方法发送 JSON Body 并注入 Token
            let item = WatchlistItemDTO(code: code, name: name)
            let _: SuccessResponse = try await APIClient.shared.send(
                path: "/api/watchlist",
                body: item
            )
            await fetchWatchlist()
        } catch {
            print("❌ Failed to add fund: \(error)")
        }
    }
    
    @MainActor
    func deleteFund(code: String) async {
        do {
            // 对齐 sse_server.py: @app.delete("/api/watchlist/{code}")
            let _: SuccessResponse = try await APIClient.shared.fetch(
                path: "/api/watchlist/\(code)",
                method: "DELETE"
            )
            await fetchWatchlist()
        } catch {
            print("❌ Failed to delete fund: \(error)")
        }
    }
}

// 补充 DTO 定义以匹配 sse_server.py
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

