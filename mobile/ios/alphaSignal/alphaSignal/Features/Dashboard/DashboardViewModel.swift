import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI
import SwiftData

@Observable
class DashboardViewModel {
    var items: [IntelligenceItem] = []
    var isStreaming = false
    var connectionStatus: String = "dashboard.connection.disconnected"
    
    // 搜索与过滤状态

    var filterMode: FilterMode = .all

    enum FilterMode {
        case all, essential, bearish, bullish
    }

    // 计算属性：应用过滤逻辑 (对齐 Web 端)
    var filteredItems: [IntelligenceItem] {
        items.filter { item in
            // 2. 模式过滤
            switch filterMode {
            case .all: return true
            case .essential: return item.urgencyScore >= 8
            case .bearish:
                let keywords = ["鹰", "利空", "下跌", "Bearish", "Hawkish", "Pressure"]
                return keywords.contains { item.sentiment.contains($0) }
            case .bullish:
                let keywords = ["鸽", "利好", "上涨", "Bullish", "Dovish", "Boost"]
                return keywords.contains { item.sentiment.contains($0) }
            }
        }
    }
    

    

    
    // SwiftData 上下文
    @ObservationIgnored
    private var persistenceContext: ModelContext?
    
    public func setModelContext(_ context: ModelContext) {
        self.persistenceContext = context
    }
    
    private let jsonDecoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()
    
    public init(modelContext: ModelContext? = nil) {
        self.persistenceContext = modelContext
    }
    
    @MainActor
    func startIntelligenceStream() async {
        guard !isStreaming else { return }
        isStreaming = true
        connectionStatus = "dashboard.connection.connecting"
        
        // 1. 先通过 REST 获取历史数据，确保页面不为空
        await fetchInitialHistory()
        
        do {
            // 从会话存储获取最新 access token
            let token = AuthTokenStore.accessToken()
            
            // 订阅 V1 高性能实时流 (基于 Redis Pub/Sub)
            let streamURL = URL(string: "http://43.139.108.187:8001/api/v1/intelligence/stream")!
            let stream = await SSEResolver.shared.subscribe(url: streamURL, token: token)
            
            connectionStatus = "dashboard.connection.live"
            
            for try await jsonString in stream {
                guard let data = jsonString.data(using: .utf8) else { continue }
                
                if let event = try? self.jsonDecoder.decode(IntelligenceEvent.self, from: data),
                   let newItems = event.data {
                    processNewItems(newItems)
                }
            }
        } catch {
            print("❌ V1 Stream failed: \(error)")
            connectionStatus = "dashboard.connection.disconnected"
            isStreaming = false
            
            // 指数退避重连逻辑
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            await startIntelligenceStream()
        }
    }
    
    @MainActor
    private func fetchInitialHistory() async {
        do {
            // 切换至 V1 Mobile BFF 接口：字段更精简，流量更省
            let response: [IntelligenceMobileReadDTO] = try await APIClient.shared.fetch(path: "/api/v1/mobile/intelligence?limit=50")
            
            // 转换为 UI 模型
            let items = response.map { dto in
                IntelligenceItem(
                    id: dto.id,
                    timestamp: dto.timestamp,
                    author: "AlphaSignal", 
                    summary: dto.summary,
                    content: "", // V1 列表页不返回正文以节省流量
                    sentiment: dto.sentiment_label,
                    urgencyScore: dto.urgency_score,
                    goldPriceSnapshot: nil
                )
            }
            processNewItems(items)
        } catch {
            print("❌ Failed to fetch V1 history: \(error)")
        }
    }
    
    @MainActor
    private func processNewItems(_ newItems: [IntelligenceItem]) {
        withAnimation(.interpolatingSpring(stiffness: 120, damping: 14)) {
            for item in newItems {
                if !self.items.contains(where: { $0.id == item.id }) {
                    self.items.append(item)
                    
                    // 同步到数据库
                    let model = IntelligenceModel(from: item)
                    persistenceContext?.insert(model)
                }
            }
            
            // 提交数据库更改
            try? persistenceContext?.save()
            
            self.items.sort { $0.timestamp > $1.timestamp }
            
            if self.items.count > 100 {
                self.items = Array(self.items.prefix(100))
            }
        }
    }
}

// 补充 DTO 定义以匹配 V1 Mobile BFF
struct IntelligenceMobileReadDTO: Codable {
    let id: Int
    let timestamp: Date
    let summary: String
    let urgency_score: Int
    let sentiment_label: String
}

struct IntelligenceHistoryResponse: Codable {
    let data: [IntelligenceItem]?
    let count: Int?
}
