import Foundation
import SwiftUI

// MARK: - Calendar Event Type

enum CalendarEventType: String, Codable, CaseIterable {
    case earnings       = "earnings"
    case dividend       = "dividend"
    case ipo            = "ipo"
    case economic       = "economic"
    case announcement   = "announcement"

    var displayName: String {
        switch self {
        case .earnings:      return String(localized: "calendar.type.earnings")
        case .dividend:      return String(localized: "calendar.type.dividend")
        case .ipo:           return String(localized: "calendar.type.ipo")
        case .economic:      return String(localized: "calendar.type.economic")
        case .announcement:  return String(localized: "calendar.type.announcement")
        }
    }

    var systemImage: String {
        switch self {
        case .earnings:      return "chart.bar.doc.horizontal"
        case .dividend:      return "dollarsign.circle"
        case .ipo:           return "star.circle"
        case .economic:      return "globe.americas"
        case .announcement:  return "megaphone"
        }
    }

    var tintColor: Color {
        switch self {
        case .earnings:      return .blue
        case .dividend:      return .green
        case .ipo:           return .purple
        case .economic:      return .orange
        case .announcement:  return .secondary
        }
    }
}

// MARK: - Impact Level

enum CalendarImpactLevel: String, Codable {
    case high   = "high"
    case medium = "medium"
    case low    = "low"

    var color: Color {
        switch self {
        case .high:   return .red
        case .medium: return .orange
        case .low:    return Color.secondary
        }
    }

    var dotColor: Color { color }
}

// MARK: - Calendar Event Model

struct CalendarEvent: Identifiable, Codable {
    let id: String
    let date: String           // "2026-03-14"
    let time: String?          // "08:30" or nil (all-day)
    let type: CalendarEventType
    let title: String
    let description: String?
    let impact: CalendarImpactLevel
    let relatedSymbols: [String]
    let isWatchlistRelated: Bool

    enum CodingKeys: String, CodingKey {
        case id, date, time, type, title, description, impact
        case relatedSymbols     = "related_symbols"
        case isWatchlistRelated = "is_watchlist_related"
    }

    var parsedDate: Date? {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.date(from: date)
    }
}

// MARK: - API Response DTO

struct CalendarAPIResponse: Codable {
    let events: [CalendarEvent]
    let dateRange: DateRangeDTO

    enum CodingKeys: String, CodingKey {
        case events
        case dateRange = "date_range"
    }

    struct DateRangeDTO: Codable {
        let from: String
        let to: String
    }
}

struct CalendarDaySummary: Identifiable {
    let date: Date
    var events: [CalendarEvent]

    var id: String { Calendar.current.startOfDay(for: date).timeIntervalSinceReferenceDate.description }

    /// Top-impact level of the day
    var topImpact: CalendarImpactLevel? {
        if events.contains(where: { $0.impact == .high })   { return .high }
        if events.contains(where: { $0.impact == .medium }) { return .medium }
        if events.contains(where: { $0.impact == .low })    { return .low }
        return nil
    }

    var hasWatchlistEvent: Bool {
        events.contains(where: { $0.isWatchlistRelated })
    }
}

// MARK: - Calendar Badge (P3 — inline in FundCompactCard)

/// Lightweight indicator shown on a watchlist row when the symbol
/// has a relevant event within the display window (≤7 days).
struct CalendarBadge {
    let label: String       // e.g. "财报" / "除权"
    let color: Color        // impact accent color
    let eventDate: Date
    let icon: String        // SF Symbol name

    static func make(from event: CalendarEvent) -> CalendarBadge? {
        guard let eventDate = event.parsedDate else { return nil }
        let label: String
        let icon: String
        switch event.type {
        case .earnings:     label = String(localized: "calendar.type.earnings");      icon = "chart.bar.doc.horizontal"
        case .dividend:     label = String(localized: "calendar.type.dividend");      icon = "dollarsign.circle"
        case .ipo:          label = String(localized: "calendar.type.ipo");           icon = "star.circle"
        case .economic:     label = String(localized: "calendar.type.economic");      icon = "globe.americas"
        case .announcement: label = String(localized: "calendar.type.announcement");  icon = "megaphone"
        }
        return CalendarBadge(label: label, color: event.impact.dotColor, eventDate: eventDate, icon: icon)
    }
}

