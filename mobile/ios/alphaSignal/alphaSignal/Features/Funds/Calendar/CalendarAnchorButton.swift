import SwiftUI
import AlphaDesign

struct CalendarAnchorButton: View {
    let viewModel: CalendarViewModel
    @Binding var isExpanded: Bool

    private var todayEvents: [CalendarEvent] {
        viewModel.events(for: Date())
    }
    
    // Top 3 impact levels for dots
    private var topImpacts: [CalendarImpactLevel] {
        var levels: [CalendarImpactLevel] = []
        if todayEvents.contains(where: { $0.impact == .high })   { levels.append(.high) }
        if todayEvents.contains(where: { $0.impact == .medium }) { levels.append(.medium) }
        if todayEvents.contains(where: { $0.impact == .low })    { levels.append(.low) }
        return Array(levels.prefix(3))
    }

    var body: some View {
        Button {
            withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                isExpanded.toggle()
            }
        } label: {
            HStack(spacing: 8) {
                // 1. Icon with subtle glow if events exist
                Image(systemName: isExpanded ? "calendar.badge.minus" : "calendar")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(todayEvents.isEmpty ? Color.secondary : Color.blue)
                    .symbolEffect(.bounce, value: isExpanded)
                
                // 2. Data Indicators
                if !todayEvents.isEmpty {
                    HStack(spacing: 3) {
                        ForEach(topImpacts.indices, id: \.self) { i in
                            Circle()
                                .fill(topImpacts[i].dotColor)
                                .frame(width: 4, height: 4)
                        }
                    }
                    
                    Text(String(localized: "calendar.anchor.count \(todayEvents.count)"))
                        .font(.system(size: 11, weight: .heavy, design: .rounded))
                        .foregroundStyle(.primary)
                } else {
                    Text("calendar.anchor.empty")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(.secondary)
                }
                
                // 3. Chevron Indicator
                Image(systemName: "chevron.right")
                    .font(.system(size: 8, weight: .black))
                    .foregroundStyle(.tertiary)
                    .rotationEffect(.degrees(isExpanded ? 90 : 0))
            }
            .padding(.leading, 10)
            .padding(.trailing, 8)
            .padding(.vertical, 8)
            .background(
                Capsule()
                    .fill(isExpanded ? Color.blue.opacity(0.1) : Color.primary.opacity(0.05))
            )
            .overlay(
                Capsule()
                    .strokeBorder(isExpanded ? Color.blue.opacity(0.2) : Color.clear, lineWidth: 1)
            )
        }
    }
}
