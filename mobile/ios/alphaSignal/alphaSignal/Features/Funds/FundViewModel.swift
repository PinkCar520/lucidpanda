import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI

enum FundSortOrder {
    case none
    case highGrowthFirst  // 涨幅榜 (原本的 descending)
    case highDropFirst    // 跌幅榜 (原本的 ascending)
}

@Observable
class FundViewModel {
    var watchlist: [FundValuation] = []
    var sortOrder: FundSortOrder = .none

    var isLoading = false
    
    var sortedWatchlist: [FundValuation] {
        let base = watchlist
        
        switch sortOrder {
        case .none:
            return base
        case .highGrowthFirst:
            // 涨幅榜：大数在前 (+5%, +2%, -1%)
            return base.sorted { $0.estimatedGrowth > $1.estimatedGrowth }
        case .highDropFirst:
            // 跌幅榜：小数（负数）在前 (-5%, -2%, +1%)
            return base.sorted { $0.estimatedGrowth < $1.estimatedGrowth }
        }
    }
    
    @MainActor
    func toggleSortOrder() {
        switch sortOrder {
        case .none: sortOrder = .highGrowthFirst
        case .highGrowthFirst: sortOrder = .highDropFirst
        case .highDropFirst: sortOrder = .none
        }
    }
    
    @MainActor
    func fetchWatchlist() async {
        isLoading = true
        do {
            let watchlistResponse: WatchlistDataResponse = try await APIClient.shared.fetch(path: "/api/v1/web/watchlist")
            let codes = watchlistResponse.data.map { $0.code }
            
            guard !codes.isEmpty else {
                self.watchlist = []
                isLoading = false
                return
            }
            
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

// DTOs
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
