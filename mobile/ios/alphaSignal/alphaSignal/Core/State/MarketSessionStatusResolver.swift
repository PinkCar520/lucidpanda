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
        let region: MarketRegion = valuation.isQdii == true ? .us : .cn
        let localStatus = status(for: region, now: now)
        
        // 核心修复逻辑：
        // 1. 如果本地时间判断显示已休市（例如现在是 21:44、或者是周末/节假日），则直接返回休市。
        //    这能有效防止展示“缓存数据”或“服务端 stale 数据”时出现的“僵尸开市”现象。
        if localStatus == .closed {
            return .closed
        }
        
        // 2. 如果本地时间认为处于交易时段（开市或午休），则尝试使用服务端的实时状态进行精确修正。
        if let serverStatus = MarketSessionStatus(serverValue: valuation.marketStatus) {
            return serverStatus
        }
        
        // 3. 服务端数据缺失或无法解析时，回退到本地推算的交易时段状态。
        return localStatus
    }

    static func status(for region: MarketRegion, now: Date = Date()) -> MarketSessionStatus {
        switch region {
        case .cn:
            return cnStatus(now: now)
        case .us:
            return usStatus(now: now)
        }
    }

    // MARK: - A 股（上交所/深交所）
    //
    // 判断优先级：
    //   1. 调休交易日（周末补班）→ 视为工作日继续判断时段
    //   2. 法定节假日（含调休休息日）→ closed
    //   3. 自然周末 → closed
    //   4. 工作日时段判断
    private static func cnStatus(now: Date) -> MarketSessionStatus {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Shanghai")!

        let ymd = cal.dateComponents([.year, .month, .day, .weekday], from: now)
        let key = dateKey(ymd.year!, ymd.month!, ymd.day!)

        // Step 1：是调休交易日（周末补班），直接走时段判断
        let isMakeupDay = cnMakeupTradingDays.contains(key)

        if !isMakeupDay {
            // Step 2：是法定假日（包括节假日调休的休息日）→ closed
            if cnPublicHolidays.contains(key) { return .closed }

            // Step 3：自然周六/周日 → closed（weekday: 1=Sun, 7=Sat in Gregorian）
            let weekday = ymd.weekday!
            if weekday == 1 || weekday == 7 { return .closed }
        }

        // Step 4：工作日时段
        let minute = minuteOfDay(now, cal: cal)
        if minute >= 9 * 60 + 30 && minute < 11 * 60 + 30 { return .open }
        if minute >= 11 * 60 + 30 && minute < 13 * 60      { return .lunchBreak }
        if minute >= 13 * 60      && minute < 15 * 60      { return .open }
        return .closed
    }

    // MARK: - 美股（QDII）
    private static func usStatus(now: Date) -> MarketSessionStatus {
        guard isWeekday(now, timeZoneId: "America/New_York") else { return .closed }
        let minute = minuteOfDay(now, timeZoneId: "America/New_York")
        if minute >= 9 * 60 + 30 && minute < 16 * 60 { return .open }
        return .closed
    }

    // MARK: - 工具方法

    private static func dateKey(_ year: Int, _ month: Int, _ day: Int) -> Int {
        year * 10000 + month * 100 + day
    }

    private static func minuteOfDay(_ date: Date, cal: Calendar) -> Int {
        let comps = cal.dateComponents([.hour, .minute], from: date)
        return comps.hour! * 60 + comps.minute!
    }

    private static func minuteOfDay(_ date: Date, timeZoneId: String) -> Int {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: timeZoneId) ?? .current
        return minuteOfDay(date, cal: cal)
    }

    private static func isWeekday(_ date: Date, timeZoneId: String) -> Bool {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: timeZoneId) ?? .current
        let weekday = cal.component(.weekday, from: date)
        return weekday >= 2 && weekday <= 6
    }

    // MARK: - A 股法定节假日（YYYYMMDD 整数，可高效 O(1) 查询）
    //
    // 数据来源：上交所/深交所官方休市公告
    // 包含：节假日本身 + 调休的休息日（周末顺延/挪移的休息）
    // 每年 12 月更新下一年日历
    //
    // ⚠️ 仅在服务端未返回 marketStatus 时作为 fallback 使用
    private static let cnPublicHolidays: Set<Int> = {
        // ----- 2025 年 -----
        let y2025: [Int] = [
            // 元旦（1 天）
            20250101,
            // 春节（1/28-2/4，调休 1/26 周日上班）
            20250128, 20250129, 20250130, 20250131,
            20250201, 20250202, 20250203, 20250204,
            // 清明节（4/4-4/6）
            20250404, 20250405, 20250406,
            // 劳动节（5/1-5/5，调休 4/27 周日上班）
            20250501, 20250502, 20250503, 20250504, 20250505,
            // 端午节（5/31-6/2）
            20250531, 20250601, 20250602,
            // 国庆 + 中秋（10/1-10/8，调休 9/28 周日、10/11 周六上班）
            20251001, 20251002, 20251003, 20251004,
            20251005, 20251006, 20251007, 20251008,
        ]

        // ----- 2026 年 -----
        // 数据来源：国务院办公厅 2025 年 11 月公告
        let y2026: [Int] = [
            // 元旦（1/1-1/3，调休 1/4 周日上班）
            20260101, 20260102, 20260103,
            // 春节（2/17-2/24，调休 2/15 周日、2/28 周六上班）
            20260217, 20260218, 20260219, 20260220,
            20260221, 20260222, 20260223, 20260224,
            // 清明节（4/5-4/6，清明当日 + 周末顺延）
            20260405, 20260406,
            // 劳动节（5/1-5/5）
            20260501, 20260502, 20260503, 20260504, 20260505,
            // 端午节（6/19-6/21）
            20260619, 20260620, 20260621,
            // 中秋节（9/25-9/27）
            20260925, 20260926, 20260927,
            // 国庆节（10/1-10/7）
            20261001, 20261002, 20261003, 20261004,
            20261005, 20261006, 20261007,
        ]

        return Set(y2025 + y2026)
    }()

    // MARK: - 调休补班交易日（自然周末但实际开市的日期）
    //
    // 这些天即使是周六/周日，A 股也正常交易
    private static let cnMakeupTradingDays: Set<Int> = [
        // 2025
        20250126, // 周日，春节调休补班
        20250208, // 周六，春节后补班（部分年份有）
        20250427, // 周日，劳动节调休补班
        20250928, // 周日，国庆调休补班
        20251011, // 周六，国庆调休补班
        // 2026
        20260104, // 周日，元旦调休补班
        20260215, // 周日，春节调休补班
        20260228, // 周六，春节调休补班
    ]
}
