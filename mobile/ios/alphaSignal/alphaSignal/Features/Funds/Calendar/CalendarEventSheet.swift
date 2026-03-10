import SwiftUI
import AlphaDesign

/// Bottom sheet presented when user taps a day in the calendar strip.
struct CalendarEventSheet: View {
    let date: Date
    let events: [CalendarEvent]
    @Environment(\.dismiss) private var dismiss

    private var dateTitle: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "M月d日（EEE）"
        formatter.locale = Locale(identifier: "zh_CN")
        return formatter.string(from: date)
    }

    private var groupedEvents: [(CalendarEventType, [CalendarEvent])] {
        let order: [CalendarEventType] = [.economic, .earnings, .dividend, .ipo, .announcement]
        var dict: [CalendarEventType: [CalendarEvent]] = [:]
        for event in events {
            dict[event.type, default: []].append(event)
        }
        return order.compactMap { type in
            guard let list = dict[type], !list.isEmpty else { return nil }
            return (type, list)
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color(.systemGroupedBackground).ignoresSafeArea()

                if events.isEmpty {
                    emptyState
                } else {
                    eventList
                }
            }
            .navigationTitle(dateTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 20))
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
        .presentationCornerRadius(24)
    }

    private var eventList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16, pinnedViews: .sectionHeaders) {
                ForEach(groupedEvents, id: \.0) { type, eventsInGroup in
                    Section {
                        VStack(spacing: 8) {
                            ForEach(eventsInGroup) { event in
                                CalendarEventCard(event: event)
                            }
                        }
                    } header: {
                        HStack(spacing: 6) {
                            Image(systemName: type.systemImage)
                                .font(.system(size: 12, weight: .bold))
                                .foregroundStyle(type.tintColor)

                            Text(type.displayName)
                                .font(.system(size: 12, weight: .bold))
                                .foregroundStyle(type.tintColor)

                            Spacer()
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 6)
                        .background(
                            Color(.systemGroupedBackground)
                                .opacity(0.95)
                        )
                    }
                }

                Spacer(minLength: 32)
            }
            .padding(.horizontal, 16)
            .padding(.top, 8)
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "calendar.badge.checkmark")
                .font(.system(size: 44))
                .foregroundStyle(.secondary.opacity(0.3))
            Text("calendar.sheet.no_events")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(.secondary)
        }
    }
}
