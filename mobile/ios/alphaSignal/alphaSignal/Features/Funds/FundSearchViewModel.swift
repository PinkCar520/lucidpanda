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
            let path = "/api/funds/search?q=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&limit=15"
            let response: [String: [FundSearchResult]] = try await APIClient.shared.fetch(path: path)
            if let searchResults = response["results"] {
                self.results = searchResults
            }
        } catch {
            print("Search failed: \(error)")
        }
        isLoading = false
    }
}
