import SwiftUI
import AlphaDesign

/// Single event card used inside the calendar event sheet.
struct CalendarEventCard: View {
    let event: CalendarEvent
    var onSymbolTap: ((String) -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 12) {
                // Impact dot + type icon column
                VStack(spacing: 4) {
                    Circle()
                        .fill(event.impact.dotColor)
                        .frame(width: 8, height: 8)
                        .padding(.top, 5)

                    Image(systemName: event.type.systemImage)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(event.type.tintColor)
                }
                .frame(width: 20)

                // Content
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        if let time = event.time {
                            Text(time)
                                .font(.system(size: 13, weight: .bold, design: .monospaced))
                                .foregroundStyle(.secondary)
                        } else {
                            Text("calendar.event.allday")
                                .font(.system(size: 13, weight: .medium))
                                .foregroundStyle(.secondary)
                        }
                        
                        if let periodLabel = event.period.localizedLabel {
                            Text("•")
                                .font(.system(size: 10))
                                .foregroundStyle(.tertiary)
                            Text(periodLabel)
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        impactBadge
                    }

                    Text(event.title)
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(.primary)
                        .lineLimit(2)

                    if let desc = event.description, !desc.isEmpty {
                        Text(desc)
                            .font(.system(size: 13))
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    
                    if let macro = event.macroDetails {
                        MacroVisualBar(details: macro)
                            .padding(.top, 4)
                    }

                    if !event.relatedSymbols.isEmpty {
                        HStack(spacing: 6) {
                            ForEach(event.relatedSymbols, id: \.self) { symbol in
                                Button {
                                    onSymbolTap?(symbol)
                                } label: {
                                    Text(symbol)
                                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(event.type.tintColor.opacity(0.12))
                                        .foregroundStyle(event.type.tintColor)
                                        .clipShape(Capsule())
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.top, 4)
                    }
                }
            }
        }
        .padding(.vertical, 6)
    }

    @ViewBuilder
    private var impactBadge: some View {
        switch event.impact {
        case .high:
            Label("calendar.impact.high", systemImage: "bolt.fill")
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.red)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.red.opacity(0.1))
                .clipShape(Capsule())
        case .medium:
            Circle()
                .fill(Color.orange)
                .frame(width: 6, height: 6)
        case .low:
            EmptyView()
        }
    }
}

struct MacroVisualBar: View {
    let details: MacroDetails
    
    private var isBetterThanExpected: Bool? {
        guard let actual = details.actual, let forecast = details.forecast else { return nil }
        // Simplified: Higher is better for most economic data, 
        // but for some (like CPI or Jobless Claims) lower is better.
        // For now, we just show the relationship.
        return actual >= forecast
    }
    
    private var color: Color {
        guard let better = isBetterThanExpected else { return .secondary }
        return better ? .green : .red
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 0) {
                metricView(label: "calendar.macro.previous", value: details.previous)
                Spacer()
                metricView(label: "calendar.macro.forecast", value: details.forecast)
                Spacer()
                metricView(label: "calendar.macro.actual", value: details.actual, isHighlight: true)
            }
            
            // Visual bar
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.secondary.opacity(0.1))
                        .frame(height: 4)
                    
                    if let actual = details.actual, let prev = details.previous, let forecast = details.forecast {
                        let totalRange = max(actual, prev, forecast) - min(actual, prev, forecast)
                        if totalRange > 0 {
                            let minV = min(actual, prev, forecast)
                            let actualPos = CGFloat((actual - minV) / totalRange) * geo.size.width
                            
                            Circle()
                                .fill(color)
                                .frame(width: 8, height: 8)
                                .offset(x: actualPos - 4)
                        }
                    }
                }
            }
            .frame(height: 8)
        }
        .padding(8)
        .background(Color.secondary.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
    
    private func metricView(label: String, value: Float?, isHighlight: Bool = false) -> some View {
        VStack(alignment: .center, spacing: 2) {
            Text(LocalizedStringKey(label))
                .font(.system(size: 9))
                .foregroundStyle(.secondary)
            if let v = value {
                Text(String(format: "%.1f", v) + (details.unit ?? ""))
                    .font(.system(size: 11, weight: isHighlight ? .heavy : .bold, design: .rounded))
                    .foregroundStyle(isHighlight ? color : .primary)
            } else {
                Text("--")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(.tertiary)
            }
        }
    }
}
