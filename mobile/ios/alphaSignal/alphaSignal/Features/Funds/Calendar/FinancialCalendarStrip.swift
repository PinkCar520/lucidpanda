import SwiftUI
import AlphaDesign

// MARK: - Financial Calendar Strip

/// Horizontal 8-day date axis embedded at the top of the watchlist.
/// Tapping a day opens `CalendarEventSheet` as a bottom sheet.
struct FinancialCalendarStrip: View {
    let viewModel: CalendarViewModel
    @State private var selectedSummary: CalendarDaySummary? = nil
    @State private var showSheet = false

    // Expose today so tests can inject
    var referenceDate: Date = Date()

    private var isAllDaysEmpty: Bool {
        !viewModel.daySummaries.isEmpty && viewModel.daySummaries.allSatisfy { $0.events.isEmpty }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Section header
            HStack(spacing: 6) {
                Image(systemName: "calendar")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
                Text("calendar.strip.title")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(.secondary)
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 6)

            if isAllDaysEmpty {
                Text("calendar.strip.empty")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 18)
            } else {
                // Day cells
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(viewModel.daySummaries) { summary in
                            DayCellView(summary: summary, referenceDate: referenceDate)
                                .onTapGesture {
                                    selectedSummary = summary
                                    showSheet = true
                                }
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 12)
                }
            }

            Divider().opacity(0.4)
        }
        .sheet(isPresented: $showSheet) {
            if let summary = selectedSummary {
                CalendarEventSheet(date: summary.date, events: summary.events)
            }
        }
    }
}

// MARK: - Static Formatters (avoid per-render allocation)

private let _weekdayFormatter: DateFormatter = {
    let f = DateFormatter()
    f.dateFormat = "EEE"
    f.locale = Locale(identifier: "zh_CN")
    return f
}()

private let _dayFormatter: DateFormatter = {
    let f = DateFormatter()
    f.dateFormat = "d"
    return f
}()

// MARK: - Day Cell View

private struct DayCellView: View {
    let summary: CalendarDaySummary
    let referenceDate: Date

    private var cal: Calendar { Calendar.current }

    private var isToday: Bool {
        cal.isDate(summary.date, inSameDayAs: referenceDate)
    }

    private var weekdayStr: String {
        _weekdayFormatter.string(from: summary.date).uppercased()
    }

    private var dayStr: String {
        _dayFormatter.string(from: summary.date)
    }

    // Dots: up to 3, sorted by impact (high first)
    private var dots: [CalendarImpactLevel] {
        var levels: [CalendarImpactLevel] = []
        if summary.events.contains(where: { $0.impact == .high })   { levels.append(.high) }
        if summary.events.contains(where: { $0.impact == .medium }) { levels.append(.medium) }
        if summary.events.contains(where: { $0.impact == .low })    { levels.append(.low) }
        return Array(levels.prefix(3))
    }

    var body: some View {
        VStack(spacing: 4) {
            // Weekday abbreviation
            Text(weekdayStr)
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(isToday ? .blue : .secondary)

            // Day number circle
            ZStack {
                if isToday {
                    Circle()
                        .fill(Color.blue)
                        .frame(width: 32, height: 32)
                } else {
                    Circle()
                        .fill(Color(.secondarySystemFill))
                        .frame(width: 32, height: 32)
                }

                Text(dayStr)
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(isToday ? .white : .primary)
            }

            // Impact dots row
            if dots.isEmpty {
                // Invisible placeholder so cells have consistent height
                Circle()
                    .fill(Color.clear)
                    .frame(width: 5, height: 5)
            } else {
                HStack(spacing: 3) {
                    ForEach(dots.indices, id: \.self) { i in
                        Circle()
                            .fill(dots[i].dotColor)
                            .frame(width: 5, height: 5)
                    }
                }
            }

            // "自选" watchlist indicator
            if summary.hasWatchlistEvent {
                Text("W")
                    .font(.system(size: 8, weight: .black, design: .monospaced))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 4)
                    .padding(.vertical, 1)
                    .background(Capsule().fill(Color.blue.opacity(0.8)))
            } else {
                Color.clear.frame(height: 12) // height placeholder
            }
        }
        .frame(width: 44)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(
                    summary.hasWatchlistEvent
                        ? Color.blue.opacity(0.06)
                        : Color(.tertiarySystemFill).opacity(0.5)
                )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .strokeBorder(
                    isToday ? Color.blue.opacity(0.4) : Color.clear,
                    lineWidth: 1.5
                )
        )
        .scaleEffect(summary.events.isEmpty ? 0.95 : 1.0)
        .animation(.spring(response: 0.3), value: summary.events.count)
    }
}
