import SwiftUI
import AlphaDesign

/// Single event card used inside the calendar event sheet.
struct CalendarEventCard: View {
    let event: CalendarEvent

    var body: some View {
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
                    // Time or all-day
                    if let time = event.time {
                        Text(time)
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundStyle(.secondary)
                    } else {
                        Text("calendar.event.allday")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    // Impact badge
                    impactBadge
                }

                Text(event.title)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(.primary)
                    .lineLimit(2)

                if let desc = event.description {
                    Text(desc)
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                // Related symbols chips
                if !event.relatedSymbols.isEmpty {
                    HStack(spacing: 6) {
                        ForEach(event.relatedSymbols, id: \.self) { symbol in
                            Text(symbol)
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(event.type.tintColor.opacity(0.12))
                                .foregroundStyle(event.type.tintColor)
                                .clipShape(Capsule())
                        }
                    }
                    .padding(.top, 2)
                }
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 14)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color(.secondarySystemGroupedBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .strokeBorder(
                    event.isWatchlistRelated
                        ? event.type.tintColor.opacity(0.3)
                        : Color.gray.opacity(0.1),
                    lineWidth: event.isWatchlistRelated ? 1.5 : 1
                )
        )
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
