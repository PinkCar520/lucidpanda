import Foundation
import AlphaData

enum MarketSessionStatus: Equatable {
    case open
    case lunchBreak
    case closed

    var localizedKey: String {
        switch self {
        case .open: return "funds.compact.market.open"
        case .lunchBreak: return "funds.compact.market.lunch_break"
        case .closed: return "funds.compact.market.closed"
        }
    }

    init?(serverValue: String?) {
        guard let raw = serverValue?.trimmingCharacters(in: .whitespacesAndNewlines), !raw.isEmpty else {
            return nil
        }

        let normalized = raw
            .replacingOccurrences(of: "-", with: "_")
            .replacingOccurrences(of: " ", with: "_")
            .uppercased()

        switch normalized {
        case "OPEN", "TRADING":
            self = .open
        case "LUNCH_BREAK", "LUNCHBREAK":
            self = .lunchBreak
        case "CLOSED", "CLOSE", "REST", "OFF":
            self = .closed
        default:
            return nil
        }
    }
}

enum MarketRegion: Equatable {
    case cn
    case us
}

enum MarketSessionStatusResolver {
    static func status(for valuation: FundValuation, now: Date = Date()) -> MarketSessionStatus {
        if let serverStatus = MarketSessionStatus(serverValue: valuation.marketStatus) {
            return serverStatus
        }
        let region: MarketRegion = valuation.isQdii == true ? .us : .cn
        return status(for: region, now: now)
    }

    static func status(for region: MarketRegion, now: Date = Date()) -> MarketSessionStatus {
        switch region {
        case .cn:
            return cnStatus(now: now)
        case .us:
            return usStatus(now: now)
        }
    }

    private static func cnStatus(now: Date) -> MarketSessionStatus {
        guard isWeekday(now, timeZoneId: "Asia/Shanghai") else { return .closed }
        let minute = minuteOfDay(now, timeZoneId: "Asia/Shanghai")
        if minute >= 9 * 60 + 30 && minute < 11 * 60 + 30 { return .open }
        if minute >= 11 * 60 + 30 && minute < 13 * 60 { return .lunchBreak }
        if minute >= 13 * 60 && minute < 15 * 60 { return .open }
        return .closed
    }

    private static func usStatus(now: Date) -> MarketSessionStatus {
        guard isWeekday(now, timeZoneId: "America/New_York") else { return .closed }
        let minute = minuteOfDay(now, timeZoneId: "America/New_York")
        if minute >= 9 * 60 + 30 && minute < 16 * 60 { return .open }
        return .closed
    }

    private static func isWeekday(_ date: Date, timeZoneId: String) -> Bool {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: timeZoneId) ?? .current
        let weekday = calendar.component(.weekday, from: date)
        return weekday >= 2 && weekday <= 6
    }

    private static func minuteOfDay(_ date: Date, timeZoneId: String) -> Int {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: timeZoneId) ?? .current
        let hour = calendar.component(.hour, from: date)
        let minute = calendar.component(.minute, from: date)
        return hour * 60 + minute
    }
}
