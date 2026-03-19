import OSLog

enum AppLog {
    static let auth = Logger(subsystem: "com.pineapple.LucidPanda", category: "Auth")
    static let root = Logger(subsystem: "com.pineapple.LucidPanda", category: "Root")
    static let watchlist = Logger(subsystem: "com.pineapple.LucidPanda", category: "Watchlist")
    static let dashboard = Logger(subsystem: "com.pineapple.LucidPanda", category: "Dashboard")
}
