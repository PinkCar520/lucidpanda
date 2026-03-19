import Foundation

struct Formatters {
    /// A static number formatter for displaying percentages with a specified number of fraction digits.
    /// Example: 12.34 -> "12.34%"
    static func percentFormatter(fractionDigits: Int) -> NumberFormatter {
        let formatter = NumberFormatter()
        formatter.numberStyle = .percent
        formatter.minimumFractionDigits = fractionDigits
        formatter.maximumFractionDigits = fractionDigits
        return formatter
    }

    /// A number formatter for displaying percentages with a "+" sign for positive numbers, configurable for fraction digits.
    /// Example: 0.1234, fractionDigits=2 -> "+12.34%"
    static func signedPercentFormatter(fractionDigits: Int) -> NumberFormatter {
        let formatter = NumberFormatter()
        formatter.numberStyle = .percent
        formatter.positivePrefix = formatter.plusSign
        formatter.minimumFractionDigits = fractionDigits
        formatter.maximumFractionDigits = fractionDigits
        return formatter
    }

    /// A static date formatter for displaying dates in "MM-dd" format.
    /// Example: 2026-02-08T12:34:56Z -> "02-08"
    static let monthDayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM-dd"
        return formatter
    }()

    /// A static date formatter for parsing "YYYY-MM-DD" date strings.
    static let yearMonthDayParser: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()
}

