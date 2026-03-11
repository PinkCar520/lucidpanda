import SwiftUI
import AlphaDesign

/// Bottom sheet presented when user taps a day in the calendar strip.
struct CalendarEventSheet: View {
    let date: Date
    let events: [CalendarEvent]
    var onSymbolTap: ((String) -> Void)? = nil
    @Environment(\.dismiss) private var dismiss

    private var dateTitle: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "M月d日 (EEE)"
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
            Group {
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
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }

    private var eventList: some View {
        List {
            ForEach(groupedEvents, id: \.0) { type, eventsInGroup in
                Section {
                    ForEach(eventsInGroup) { event in
                        CalendarEventCard(event: event) { symbol in
                            onSymbolTap?(symbol)
                            dismiss()
                        }
                    }
                }
 header: {
                    HStack(spacing: 6) {
                        Image(systemName: type.systemImage)
                        Text(type.displayName)
                    }
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(type.tintColor)
                    .textCase(nil)
                }
            }
        }
        .listStyle(.insetGrouped) // Apple 原生 List 分组排版，去除了自定义的安卓感卡片
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
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
    }
}
