import SwiftUI
import AlphaData
import AlphaDesign

struct SectorDetailView: View {
    let sectorName: String
    let stat: SectorStat
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Header Info
                    HStack(spacing: 16) {
                        VStack(alignment: .leading) {
                            Text("funds.sector.metric.weight")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                            Text(String(format: "%.2f%%", stat.weight))
                                .font(.system(size: 20, weight: .semibold, design: .monospaced))
                        }
                        
                        Divider().frame(height: 30)
                        
                        VStack(alignment: .leading) {
                            Text("funds.sector.metric.contribution")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                            let formattedImpact = Formatters.signedPercentFormatter(fractionDigits: 3).string(from: NSNumber(value: stat.impact / 100.0)) ?? "\(stat.impact.formatted(.number.precision(.fractionLength(3))))%"
                            Text(formattedImpact)
                                .font(.system(size: 20, weight: .semibold, design: .monospaced))
                                .foregroundStyle(stat.impact >= 0 ? Color.Alpha.up : Color.Alpha.down)
                        }
                        Spacer()
                    }
                    .padding()
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    
                    Text("funds.sector.components.title")
                        .font(.system(size: 14, weight: .medium))
                        .padding(.top)
                    
                    if let subItems = stat.sub, !subItems.isEmpty {
                        let sortedItems = subItems.sorted { $0.value.impact > $1.value.impact }
                        
                        VStack(spacing: 12) {
                            ForEach(sortedItems, id: \.key) { name, subStat in
                                LiquidGlassCard {
                                    HStack {
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text(subStat.id.map { LocalizedStringKey("sector.name.\($0)") } ?? LocalizedStringKey(name))
                                                .font(.system(size: 14, weight: .medium))
                                            Text(
                                                String(
                                                    format: NSLocalizedString("funds.sector.position_format", comment: ""),
                                                    subStat.weight
                                                )
                                            )
                                            .font(.system(size: 10))
                                            .foregroundStyle(.secondary)
                                        }
                                        Spacer()
                                        let formattedImpact = Formatters.signedPercentFormatter(fractionDigits: 3).string(from: NSNumber(value: subStat.impact / 100.0)) ?? "\(subStat.impact.formatted(.number.precision(.fractionLength(3))))%"
                                        Text(formattedImpact)
                                            .font(.system(size: 14, weight: .medium, design: .monospaced))
                                            .foregroundStyle(subStat.impact >= 0 ? Color.Alpha.up : Color.Alpha.down)
                                    }
                                }
                            }
                        }
                    } else {
                        Text("funds.sector.empty")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .center)
                            .padding()
                    }
                }
                .padding()
            }
            .navigationTitle(stat.id.map { LocalizedStringKey("sector.name.\($0)") } ?? LocalizedStringKey(sectorName))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
            }
        }
    }
}

