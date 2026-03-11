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
    // "E" produces "周一", "周二" in zh_CN. 
    // We want just "一", "二", "三"
    f.dateFormat = "E"
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
        // "周一" -> "一"
        let str = _weekdayFormatter.string(from: summary.date)
        return str.replacingOccurrences(of: "周", with: "")
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
        VStack(spacing: 8) {
            // Weekday (Just "一", "二")
            Text(weekdayStr)
                .font(.system(size: 11, weight: isToday ? .bold : .medium))
                .foregroundStyle(isToday ? .blue : .secondary.opacity(0.8))

            // Day Number
            Text(dayStr)
                .font(.system(size: 18, weight: isToday ? .heavy : .bold, design: .rounded))
                .foregroundStyle(isToday ? .blue : .primary)

            // Event Dots (Minimalist Track)
            HStack(spacing: 4) {
                if dots.isEmpty {
                    Circle().fill(Color.clear).frame(width: 4, height: 4) // Invisible placeholder
                } else {
                    ForEach(dots.indices, id: \.self) { i in
                        Circle()
                            .fill(dots[i].dotColor)
                            .frame(width: 4, height: 4)
                    }
                }
            }
            .frame(height: 4)
        }
        .frame(width: 40, height: 64)
        // Completely transparent background per minimal design
        .background(Color.clear)
        // Watchlist indicator - a sleek corner dot instead of a big "W" capsule
        .overlay(alignment: .topTrailing) {
            if summary.hasWatchlistEvent {
                Circle()
                    .fill(Color.blue)
                    .frame(width: 5, height: 5)
                    .offset(x: -2, y: 12) // Adjusted to sit nicely next to the date number
            }
        }
        .scaleEffect(summary.events.isEmpty ? 0.98 : 1.0)
        .animation(.spring(response: 0.3), value: summary.events.count)
    }
}
