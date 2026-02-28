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
    
    private var searchTask: Task<Void, Never>?
    
    @MainActor
    func performSearch() async {
        // 取消上一次正在排队或者还在请求当中的任务（防止竞态请求并行发往服务器！）
        searchTask?.cancel()
        
        guard query.count >= 2 else {
            searchTask = nil
            results = []
            isLoading = false
            return
        }
        
        isLoading = true
        
        let task = Task { @MainActor in
            do {
                // 【核心修复：防抖】将之前的 300ms 降低为 100ms，在防卡顿和极速响应之间取得完美平衡
                try await Task.sleep(nanoseconds: 100_000_000)
            } catch {
                // 如果在 300ms 内用户又按了键盘，这个休眠直接抛异常中断
                return
            }
            
            guard !Task.isCancelled else { return }
            
            do {
                let path = "/api/v1/web/funds/search?q=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&limit=15"
                let response: FundSearchResponse = try await APIClient.shared.fetch(path: path)
                
                // 【核心修复：防竞态渲染】网络请求回来了，但如果用户在此期间改了输入框：抛弃这批旧数据
                guard !Task.isCancelled else { return }
                
                self.results = response.results
            } catch {
                guard !Task.isCancelled else { return }
                print("❌ Search failed: \(error)")
                self.results = []
            }
            
            guard !Task.isCancelled else { return }
            self.isLoading = false
        }
        
        self.searchTask = task
        await task.value
    }
}

// 匹配 sse_server.py 的返回结构
struct FundSearchResponse: Codable {
    let results: [FundSearchResult]
    let total: Int
    let query: String
}
