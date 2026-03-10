import Foundation
import Observation
import AlphaCore

@Observable
final class CalendarViewModel {

    // MARK: - Published State

    var daySummaries: [CalendarDaySummary] = []
    var selectedDate: Date? = nil
    var isLoading: Bool = false
    var errorMessage: String? = nil

    // MARK: - Init

    init() {
        buildDaySummaries(from: Self.mockEvents())
    }

    // MARK: - Public

    func load() async {
        await MainActor.run { isLoading = true }
        defer { Task { @MainActor in isLoading = false } }

        do {
            let today = Date()
            let toDate = Calendar.current.date(byAdding: .day, value: 7, to: today)!
            let fmt = DateFormatter()
            fmt.dateFormat = "yyyy-MM-dd"
            let from = fmt.string(from: today)
            let to   = fmt.string(from: toDate)

            let path = "/api/v1/calendar/events?date_from=\(from)&date_to=\(to)"
            let response: CalendarAPIResponse = try await APIClient.shared.fetch(path: path)
            await MainActor.run {
                buildDaySummaries(from: response.events)
            }
        } catch {
            // Network unavailable or server error — fall back to mock data
            let fallback = Self.mockEvents()
            await MainActor.run {
                buildDaySummaries(from: fallback)
                errorMessage = error.localizedDescription
            }
        }
    }

    func events(for date: Date) -> [CalendarEvent] {
        let cal = Calendar.current
        return daySummaries
            .first(where: { cal.isDate($0.date, inSameDayAs: date) })?
            .events ?? []
    }

    /// Returns the highest-priority upcoming badge for a given fund code
    /// within the loaded 7-day window (earnings > dividend > ipo > others).
    func badge(for fundCode: String) -> CalendarBadge? {
        let symbol = fundCode.uppercased()
        let priorityOrder: [CalendarEventType] = [.earnings, .dividend, .ipo, .economic, .announcement]

        // Collect all events related to this symbol across all days
        let allSymbolEvents = daySummaries.flatMap { $0.events }.filter { event in
            event.relatedSymbols.map { $0.uppercased() }.contains(symbol)
        }

        // Pick the earliest event of the highest-priority type
        for type in priorityOrder {
            let typeEvents = allSymbolEvents
                .filter { $0.type == type }
                .compactMap { event -> (CalendarEvent, Date)? in
                    guard let d = event.parsedDate else { return nil }
                    return (event, d)
                }
                .sorted { $0.1 < $1.1 }

            if let (event, _) = typeEvents.first {
                return CalendarBadge.make(from: event)
            }
        }
        return nil
    }


    // MARK: - Private

    private func buildDaySummaries(from events: [CalendarEvent]) {
        let cal = Calendar.current
        let today = cal.startOfDay(for: Date())
        // Build 7-day window: today … today+6
        let window: [Date] = (0..<8).compactMap { cal.date(byAdding: .day, value: $0, to: today) }

        daySummaries = window.map { day in
            let dayEvents = events.filter { event in
                guard let d = event.parsedDate else { return false }
                return cal.isDate(d, inSameDayAs: day)
            }
            return CalendarDaySummary(date: day, events: dayEvents)
        }
    }

    // MARK: - Mock Data (P0)

    static func mockEvents() -> [CalendarEvent] {
        let cal = Calendar.current
        let today = Date()

        func dateStr(daysOffset: Int) -> String {
            let date = cal.date(byAdding: .day, value: daysOffset, to: today)!
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            return formatter.string(from: date)
        }

        return [
            // Today - high impact economic
            CalendarEvent(
                id: "ev-1",
                date: dateStr(daysOffset: 0),
                time: "08:30",
                type: .economic,
                title: String(localized: "calendar.mock.cpi"),
                description: String(localized: "calendar.mock.cpi.desc"),
                impact: .high,
                relatedSymbols: [],
                isWatchlistRelated: false
            ),
            // Today - medium watchlist earnings
            CalendarEvent(
                id: "ev-2",
                date: dateStr(daysOffset: 0),
                time: nil,
                type: .earnings,
                title: "AAPL " + String(localized: "calendar.event.earnings_release"),
                description: String(localized: "calendar.mock.aapl.desc"),
                impact: .medium,
                relatedSymbols: ["AAPL"],
                isWatchlistRelated: true
            ),
            // Tomorrow - Fed meeting
            CalendarEvent(
                id: "ev-3",
                date: dateStr(daysOffset: 1),
                time: "14:00",
                type: .economic,
                title: String(localized: "calendar.mock.fed"),
                description: nil,
                impact: .high,
                relatedSymbols: [],
                isWatchlistRelated: false
            ),
            // Day+2 - dividend
            CalendarEvent(
                id: "ev-4",
                date: dateStr(daysOffset: 2),
                time: nil,
                type: .dividend,
                title: "MSFT " + String(localized: "calendar.event.ex_dividend"),
                description: nil,
                impact: .low,
                relatedSymbols: ["MSFT"],
                isWatchlistRelated: true
            ),
            // Day+3 - IPO
            CalendarEvent(
                id: "ev-5",
                date: dateStr(daysOffset: 3),
                time: nil,
                type: .ipo,
                title: String(localized: "calendar.mock.ipo"),
                description: nil,
                impact: .medium,
                relatedSymbols: [],
                isWatchlistRelated: false
            ),
            // Day+5 - Non-Farm Payrolls
            CalendarEvent(
                id: "ev-6",
                date: dateStr(daysOffset: 5),
                time: "08:30",
                type: .economic,
                title: String(localized: "calendar.mock.nfp"),
                description: nil,
                impact: .high,
                relatedSymbols: [],
                isWatchlistRelated: false
            ),
        ]
    }
}
