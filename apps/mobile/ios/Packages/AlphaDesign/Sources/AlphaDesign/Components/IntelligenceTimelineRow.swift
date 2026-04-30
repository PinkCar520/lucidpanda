import SwiftUI
import AlphaData

public struct IntelligenceTimelineRow: View {
    let item: FundRelatedIntelligence
    let isFirst: Bool
    let isLast: Bool

    public init(item: FundRelatedIntelligence, isFirst: Bool, isLast: Bool) {
        self.item = item
        self.isFirst = isFirst
        self.isLast = isLast
    }

    private var sentimentColor: Color {
        switch item.sentiment {
        case "bullish": return Color.Alpha.up
        case "bearish": return Color.Alpha.down
        default: return .secondary
        }
    }

    private var sentimentLabel: String {
        switch item.sentiment {
        case "bullish": return "看多"
        case "bearish": return "看空"
        default: return "中性"
        }
    }

    public var body: some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(spacing: 0) {
                Rectangle()
                    .fill(Color.secondary.opacity(isFirst ? 0 : 0.25))
                    .frame(width: 2, height: 14)
                
                if let icon = item.categoryIcon {
                    ZStack {
                        Circle()
                            .fill(sentimentColor)
                            .frame(width: 20, height: 20)
                        Image(systemName: icon)
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.white)
                    }
                    .overlay(Circle().stroke(.white.opacity(0.9), lineWidth: 1))
                } else {
                    Circle()
                        .fill(sentimentColor)
                        .frame(width: 12, height: 12)
                        .overlay(Circle().stroke(.white.opacity(0.9), lineWidth: 1))
                }

                Rectangle()
                    .fill(Color.secondary.opacity(isLast ? 0 : 0.25))
                    .frame(width: 2, height: 54)
            }

            VStack(alignment: .leading, spacing: 6) {
                if let category = item.category {
                    Text(LocalizedStringKey("intelligence.category.\(category.lowercased())"))
                        .font(.system(size: 9, weight: .black))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(sentimentColor.opacity(0.1))
                        .foregroundStyle(sentimentColor)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                        .padding(.bottom, 2)
                }

                Text(item.summary)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .lineLimit(2)

                if let advice = item.advice, !advice.isEmpty {
                    Text(advice)
                        .font(.system(size: 13))
                        .foregroundStyle(Color.Alpha.textSecondary)
                        .lineLimit(2)
                }

                HStack(spacing: 10) {
                    Text(item.timestamp.formatted(date: .numeric, time: .shortened))
                        .font(.system(size: 11, design: .monospaced))
                        .foregroundStyle(Color.Alpha.taupe)

                    Text(item.urgencyScore >= 8 ? "高优先级" : "一般")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(item.urgencyScore >= 8 ? Color.Alpha.down : Color.Alpha.taupe)

                    Text(sentimentLabel)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(sentimentColor)
                }
            }
            .padding(.top, 2)
            .padding(.bottom, isLast ? 0 : 10)
            Spacer(minLength: 0)
        }
    }
}

public struct IntelligenceTimelinePlaceholderRow: View {
    let title: String
    let subtitle: String

    public init(title: String, subtitle: String) {
        self.title = title
        self.subtitle = subtitle
    }

    public var body: some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(spacing: 0) {
                Rectangle()
                    .fill(Color.secondary.opacity(0.25))
                    .frame(width: 2, height: 14)
                Circle()
                    .fill(Color.secondary.opacity(0.5))
                    .frame(width: 12, height: 12)
                Rectangle()
                    .fill(Color.secondary.opacity(0.25))
                    .frame(width: 2, height: 32)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text(title)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(Color.Alpha.textSecondary)
                Text(subtitle)
                    .font(.system(size: 12))
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.8))
            }
            .padding(.top, 2)
            Spacer(minLength: 0)
        }
    }
}
