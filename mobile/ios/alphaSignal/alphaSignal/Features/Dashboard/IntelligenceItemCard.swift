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
                    .background(item.urgencyScore >= 8 ? Color.red.opacity(0.1) : Color.blue.opacity(0.1))
                    .foregroundStyle(item.urgencyScore >= 8 ? Color.red : Color.blue)
                    .clipShape(Capsule())
                    
                    Spacer()
                    
                    Text(item.timestamp.formatted(.relative(presentation: .numeric, unitsStyle: .narrow)))
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.gray.opacity(0.6))
                }
                
                VStack(alignment: .leading, spacing: 6) {
                    Text(item.summary)
                        .font(.headline)
                        .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                        .lineLimit(2)
                    
                    Text(item.content)
                        .font(.caption)
                        .foregroundStyle(.gray)
                        .lineLimit(3)
                        .multilineTextAlignment(.leading)
                }
                
                HStack {
                    Label(item.author, systemImage: "person.circle.fill")
                        .foregroundStyle(.gray.opacity(0.7))
                    
                    Spacer()
                    
                    if let price = item.goldPriceSnapshot {
                        HStack(spacing: 4) {
                            Text("dashboard.asset.gold")
                                .font(.system(size: 8, weight: .bold))
                                .padding(.horizontal, 4)
                                .padding(.vertical, 2)
                                .background(Color.black.opacity(0.03))
                                .cornerRadius(4)
                            
                            Text("$\(String(format: "%.1f", price))")
                                .fontWeight(.black)
                        }
                        .foregroundStyle(.blue)
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
