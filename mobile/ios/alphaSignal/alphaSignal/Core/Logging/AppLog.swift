import OSLog

enum AppLog {
    static let auth = Logger(subsystem: "com.pineapple.alphaSignal", category: "Auth")
    static let root = Logger(subsystem: "com.pineapple.alphaSignal", category: "Root")
    static let watchlist = Logger(subsystem: "com.pineapple.alphaSignal", category: "Watchlist")
    static let dashboard = Logger(subsystem: "com.pineapple.alphaSignal", category: "Dashboard")
}
