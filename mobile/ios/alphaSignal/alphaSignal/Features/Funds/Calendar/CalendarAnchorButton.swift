import SwiftUI
import AlphaDesign

struct CalendarAnchorButton: View {
    let viewModel: CalendarViewModel
    @Binding var isExpanded: Bool

    private var todayEvents: [CalendarEvent] {
        viewModel.events(for: Date())
    }

    private var impactLevels: [CalendarImpactLevel] {
        var levels: [CalendarImpactLevel] = []
        if todayEvents.contains(where: { $0.impact == .high }) { levels.append(.high) }
        if todayEvents.contains(where: { $0.impact == .medium }) { levels.append(.medium) }
        if todayEvents.contains(where: { $0.impact == .low }) { levels.append(.low) }
        return Array(levels.prefix(3))
    }

    var body: some View {
        Button {
            withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                isExpanded.toggle()
            }
        } label: {
            HStack(spacing: 4) {
                Image(systemName: "calendar")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(todayEvents.isEmpty ? Color.secondary : Color.blue)

                if todayEvents.isEmpty {
                    Text("calendar.anchor.empty")
                        .font(.system(size: 11))
                        .foregroundStyle(Color.secondary)
                        .lineLimit(1)
                } else {
                    HStack(spacing: 2) {
                        ForEach(impactLevels, id: \.self) { level in
                            Circle()
                                .fill(level.dotColor)
                                .frame(width: 5, height: 5)
                        }
                    }

                    Text(String(format: String(localized: "calendar.anchor.count"), Int64(todayEvents.count)))
                        .font(.system(size: 11, weight: .bold, design: .rounded))
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                }

                Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(Color.secondary)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .glassEffect(.regular, in: .capsule)
        }
        .buttonStyle(.plain)
    }
}
