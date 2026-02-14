import SwiftUI
import AlphaDesign
import AlphaData

struct IntelligenceItemCard: View {
    let item: IntelligenceItem
    
    var body: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    HStack(spacing: 4) {
                        Image(systemName: "bolt.fill")
                        Text("\(item.urgencyScore)")
                    }
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(item.urgencyScore >= 8 ? Color.red.opacity(0.12) : Color(uiColor: .secondarySystemFill))
                    .foregroundStyle(item.urgencyScore >= 8 ? Color.red : Color.primary)
                    .clipShape(Capsule())
                    
                    Spacer()
                    
                    Text(item.timestamp.formatted(.relative(presentation: .numeric, unitsStyle: .narrow)))
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                
                VStack(alignment: .leading, spacing: 6) {
                    Text(item.summary)
                        .font(.headline)
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                    
                    Text(item.content)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                        .multilineTextAlignment(.leading)
                }
                
                HStack {
                    Label(item.author, systemImage: "person.circle.fill")
                        .foregroundStyle(.secondary)
                    
                    Spacer()
                    
                    if let price = item.goldPriceSnapshot {
                        HStack(spacing: 4) {
                            Text("dashboard.asset.gold")
                                .font(.system(size: 8, weight: .bold))
                                .padding(.horizontal, 4)
                                .padding(.vertical, 2)
                                .background(Color(uiColor: .tertiarySystemFill))
                                .cornerRadius(4)
                            
                            Text("$\(String(format: "%.1f", price))")
                                .fontWeight(.black)
                        }
                        .foregroundStyle(.primary)
                    }
                }
                .font(.system(size: 10, design: .monospaced))
                .padding(.top, 4)
            }
        }
        .transition(.asymmetric(
            insertion: .move(edge: .top).combined(with: .opacity).combined(with: .scale(scale: 0.9)),
            removal: .opacity
        ))
    }
}
