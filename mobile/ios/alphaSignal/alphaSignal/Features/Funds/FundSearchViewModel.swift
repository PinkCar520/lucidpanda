import Foundation
import Observation
import AlphaCore
import AlphaData
import Combine

@Observable
class FundSearchViewModel {
    var query = ""
    var results: [FundSearchResult] = []
    var isLoading = false
    
    @MainActor
    func performSearch() async {
        guard query.count >= 2 else {
            results = []
            return
        }
        
        isLoading = true
        do {
            let path = "/api/v1/web/funds/search?q=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&limit=15"
            let response: FundSearchResponse = try await APIClient.shared.fetch(path: path)
            self.results = response.results
        } catch {
            print("❌ Search failed: \(error)")
        }
        isLoading = false
    }
}

// 匹配 sse_server.py 的返回结构
struct FundSearchResponse: Codable {
    let results: [FundSearchResult]
    let total: Int
    let query: String
}
