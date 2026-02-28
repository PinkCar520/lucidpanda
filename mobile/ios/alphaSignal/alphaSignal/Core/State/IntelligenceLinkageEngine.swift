import Foundation
import SwiftData
import AlphaData

/// 生产级情报关联引擎
/// 负责在本地 SwiftData 中检索与特定基金持仓相关的地缘政治情报
public struct IntelligenceLinkageEngine {
    private let modelContext: ModelContext
    
    public init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }
    
    /// 获取关联情报
    /// 逻辑：
    /// 1. 获取基金持仓代码列表
    /// 2. 在情报摘要或内容中模糊匹配相关资产关键词 (如: "黄金", "Gold", "AU2406")
    /// 3. 过滤高评分情报 (> 7.0)
    public func fetchLinkedIntelligence(for valuation: FundValuation) -> [IntelligenceItem] {
        let components = valuation.components.map { $0.name }
        // 动态关键词选取：基金名称本身及前五大重仓资产，剔除无效的硬编码全局宏观词汇
        let allKeywords = [valuation.fundName] + components.prefix(5)
        
        let descriptor = FetchDescriptor<IntelligenceModel>(
            predicate: #Predicate<IntelligenceModel> { model in
                model.urgencyScore >= 7
            },
            sortBy: [SortDescriptor(\.timestamp, order: .reverse)]
        )
        
        do {
            let cachedModels = try modelContext.fetch(descriptor)
            
            // 在内存中进行更细致的文本关键词匹配 (SwiftData Predicate 对模糊匹配支持有限)
            return cachedModels.filter { model in
                allKeywords.contains { keyword in
                    model.summary.contains(keyword) || model.content.contains(keyword)
                }
            }.prefix(5).map { IntelligenceItem(from: $0) }
            
        } catch {
            return []
        }
    }
}
