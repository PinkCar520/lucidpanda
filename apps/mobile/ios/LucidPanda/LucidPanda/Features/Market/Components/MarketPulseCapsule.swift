// mobile/ios/LucidPanda/LucidPanda/Features/Market/Components/MarketPulseCapsule.swift
import SwiftUI
import AlphaDesign
import AlphaData

struct MarketPulseCapsule: View {
    let viewModel: MarketPulseViewModel
    @State private var showPulseSheet = false
    
    var body: some View {
        Button(action: { 
            let generator = UIImpactFeedbackGenerator(style: .medium)
            generator.impactOccurred()
            showPulseSheet = true 
        }) {
            HStack(spacing: 8) {
                // 呼吸灯效果的气泡图标
                ZStack {
                    Circle()
                        .fill(sentimentColor(viewModel.pulseData?.overallSentiment ?? "neutral").opacity(0.3))
                        .frame(width: 12, height: 12)
                        .scaleEffect(isAnimating ? 1.4 : 1.0)
                        .opacity(isAnimating ? 0.2 : 0.8)
                    
                    Circle()
                        .fill(sentimentColor(viewModel.pulseData?.overallSentiment ?? "neutral"))
                        .frame(width: 6, height: 6)
                }
                .onAppear {
                    withAnimation(.easeInOut(duration: 2.0).repeatForever(autoreverses: true)) {
                        isAnimating = true
                    }
                }
                
                Text("dashboard.market_pulse.label")
                    .font(.system(size: 10, weight: .semibold, design: .monospaced))
                    .foregroundStyle(.primary)

                if let data = viewModel.pulseData {
                    Text(data.overallSentimentZh)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(sentimentColor(data.overallSentiment))
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(.ultraThinMaterial)
            .clipShape(Capsule())
            .overlay(
                Capsule()
                    .stroke(Color.primary.opacity(0.1), lineWidth: 0.5)
            )
        }
        .task {
            await viewModel.start()
        }
        .sheet(isPresented: $showPulseSheet) {
            MarketPulseSheet(viewModel: viewModel)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
    }
    
    @State private var isAnimating = false
    
    private func sentimentColor(_ sentiment: String) -> Color {
        switch sentiment {
        case "bullish": return Color.Alpha.down // 红色 (中国习惯)
        case "bearish": return Color.Alpha.up   // 绿色 (中国习惯)
        default: return Color.Alpha.neutral
        }
    }
}
