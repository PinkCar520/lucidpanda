import SwiftUI
import AlphaData
import AlphaDesign

struct SectorDetailView: View {
    let sectorName: String
    let stat: SectorStat
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        // Header Info
                        HStack(spacing: 16) {
                            VStack(alignment: .leading) {
                                Text("行业权重")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                Text(String(format: "%.2f%%", stat.weight))
                                    .font(.system(size: 20, weight: .black, design: .monospaced))
                            }
                            
                            Divider().frame(height: 30)
                            
                            VStack(alignment: .leading) {
                                Text("贡献度")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                Text(String(format: "%+.3f%%", stat.impact))
                                    .font(.system(size: 20, weight: .black, design: .monospaced))
                                    .foregroundStyle(stat.impact >= 0 ? .red : .green)
                            }
                            Spacer()
                        }
                        .padding()
                        .background(.ultraThinMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                        
                        Text("成分股穿透")
                            .font(.system(size: 14, weight: .bold))
                            .padding(.top)
                        
                        if let subItems = stat.sub, !subItems.isEmpty {
                            let sortedItems = subItems.sorted { $0.value.impact > $1.value.impact }
                            
                            VStack(spacing: 12) {
                                ForEach(sortedItems, id: \.key) { name, subStat in
                                    LiquidGlassCard {
                                        HStack {
                                            VStack(alignment: .leading, spacing: 4) {
                                                Text(name)
                                                    .font(.system(size: 14, weight: .bold))
                                                Text(String(format: "仓位: %.2f%%", subStat.weight))
                                                    .font(.system(size: 10))
                                                    .foregroundStyle(.secondary)
                                            }
                                            Spacer()
                                            Text(String(format: "%+.3f%%", subStat.impact))
                                                .font(.system(size: 14, weight: .bold, design: .monospaced))
                                                .foregroundStyle(subStat.impact >= 0 ? .red : .green)
                                        }
                                    }
                                }
                            }
                        } else {
                            Text("暂无底层成分数据")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .frame(maxWidth: .infinity, alignment: .center)
                                .padding()
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle(sectorName)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("关闭") { dismiss() }
                        .font(.subheadline.bold())
                }
            }
        }
    }
}
