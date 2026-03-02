// mobile/ios/alphaSignal/alphaSignal/Features/Market/Components/MarketQuoteCard.swift
import SwiftUI
import AlphaData
import AlphaDesign

/// 单个品种报价卡片
struct MarketQuoteCard: View {
    let quote: MarketQuote
    let symbol: SymbolType
    let onTap: (() -> Void)?
    
    enum SymbolType: String, CaseIterable {
        case gold = "GC=F"
        case dxy = "DXY"
        case oil = "CL=F"
        case us10y = "US10Y"
        
        var displayName: String {
            switch self {
            case .gold: return "黄金"
            case .dxy: return "美元指数"
            case .oil: return "原油"
            case .us10y: return "美债 10Y"
            }
        }
        
        var icon: String {
            switch self {
            case .gold: return "circle.fill"
            case .dxy: return "globe"
            case .oil: return "drop.fill"
            case .us10y: return "chart.line.uptrend.xyaxis"
            }
        }
        
        var primaryColor: Color {
            switch self {
            case .gold: return Color(.systemYellow)
            case .dxy: return Color(.systemBlue)
            case .oil: return Color(.systemOrange)
            case .us10y: return Color(.systemPurple)
            }
        }
    }
    
    var body: some View {
        Button(action: { onTap?() }) {
            VStack(alignment: .leading, spacing: 10) {
                // 顶部：品种名称 + 图标
                HStack {
                    Image(systemName: symbol.icon)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(symbol.primaryColor)
                    
                    Text(symbol.displayName)
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(.secondary)
                    
                    Spacer()
                    
                    // 实时状态点
                    Circle()
                        .fill(quote.change >= 0 ? Color.red : Color.green)
                        .frame(width: 6, height: 6)
                }
                
                // 价格
                Text(formatPrice(quote.price))
                    .font(.system(size: 22, weight: .bold, design: .monospaced))
                    .foregroundStyle(.primary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                
                // 涨跌幅
                HStack(spacing: 4) {
                    let isPositive = quote.change >= 0
                    Image(systemName: isPositive ? "arrow.up.right" : "arrow.down.right")
                        .font(.system(size: 10, weight: .bold))

                    Text(quote.formattedChange)
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                }
                .foregroundStyle(quote.change >= 0 ? Color.red : Color.green)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(
                    RoundedRectangle(cornerRadius: 4)
                        .fill((quote.change >= 0 ? Color.red : Color.green).opacity(0.1))
                )
                
                Spacer()
                
                // 24 小时高低
                if let high = quote.high24h, let low = quote.low24h {
                    HStack {
                        Text("24h 高")
                            .font(.system(size: 9))
                            .foregroundStyle(.tertiary)
                        Text(formatPrice(high))
                            .font(.system(size: 9, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        
                        Spacer()
                        
                        Text("24h 低")
                            .font(.system(size: 9))
                            .foregroundStyle(.tertiary)
                        Text(formatPrice(low))
                            .font(.system(size: 9, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .padding(14)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(Color(.systemBackground))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .strokeBorder(
                        LinearGradient(
                            colors: [.white.opacity(0.2), .clear],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 1
                    )
            )
            .shadow(color: .black.opacity(0.04), radius: 8, x: 0, y: 4)
        }
        .buttonStyle(.plain)
    }
    
    private func formatPrice(_ price: Double) -> String {
        // 根据品种调整价格精度
        switch symbol {
        case .us10y:
            return String(format: "%.3f", price)
        case .dxy:
            return String(format: "%.3f", price)
        default:
            return String(format: "%.2f", price)
        }
    }
}

// MARK: - Preview

#Preview {
    VStack(spacing: 16) {
        MarketQuoteCard(
            quote: MarketQuote(
                symbol: "GC=F",
                name: "黄金",
                price: 2685.50,
                change: 12.30,
                changePercent: 0.46,
                high24h: 2692.00,
                low24h: 2670.20,
                open: 2673.20,
                previousClose: 2673.20,
                timestamp: Date()
            ),
            symbol: .gold,
            onTap: nil
        )
        .frame(height: 160)
        
        MarketQuoteCard(
            quote: MarketQuote(
                symbol: "DXY",
                name: "美元指数",
                price: 106.85,
                change: -0.32,
                changePercent: -0.30,
                high24h: 107.30,
                low24h: 106.70,
                open: 107.17,
                previousClose: 107.17,
                timestamp: Date()
            ),
            symbol: .dxy,
            onTap: nil
        )
        .frame(height: 160)
    }
    .padding()
    .background(Color(.systemGray6))
}
