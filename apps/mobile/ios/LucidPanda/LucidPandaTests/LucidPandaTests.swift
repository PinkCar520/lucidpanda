//
//  LucidPandaTests.swift
//  LucidPandaTests
//
//  Created by 草莓凤梨 on 2/8/26.
//

import Testing
@testable import LucidPanda
import AlphaData
import Foundation

struct LucidPandaTests {

    @MainActor
    @Test("登录基线: 表单可提交规则")
    func loginBaselineValidation() async throws {
        let vm = LoginViewModel()

        vm.mode = .login
        vm.email = ""
        vm.password = ""
        #expect(vm.canSubmit == false)

        vm.email = "qa@example.com"
        vm.password = "12345678"
        #expect(vm.canSubmit == true)

        vm.mode = .register
        vm.username = "qa_user"
        vm.confirmPassword = "12345678"
        #expect(vm.canSubmit == true)

        vm.confirmPassword = "mismatch"
        #expect(vm.canSubmit == false)

        vm.mode = .forgotPassword
        vm.email = "qa@example.com"
        #expect(vm.canSubmit == true)
    }

    @MainActor
    @Test("登出基线: 状态与会话清理")
    func logoutBaselineStateTransition() async throws {
        AuthTokenStore.clear()
        try? AuthTokenStore.saveSession(
            accessToken: "test_access",
            refreshToken: "test_refresh",
            expiresIn: 3600
        )

        let vm = AppRootViewModel()
        vm.currentState = .authenticated
        vm.userProfile = UserProfileDTO(
            id: "u1",
            email: "qa@example.com",
            username: "qa_user",
            name: nil,
            nickname: nil,
            gender: nil,
            birthday: nil,
            location: nil,
            languagePreference: nil,
            displayName: nil,
            createdAt: nil,
            avatarUrl: nil,
            isTwoFaEnabled: nil
        )

        vm.updateState(to: .unauthenticated)

        #expect(vm.currentState == .unauthenticated)
        #expect(vm.userProfile == nil)
        #expect(AuthTokenStore.accessToken() == nil)
        #expect(AuthTokenStore.refreshToken() == nil)
    }

    @MainActor
    @Test("基金列表基线: 分组过滤与排序")
    func fundListBaselineSortAndFilter() async throws {
        let vm = FundViewModel()

        let a = FundValuation(
            fundCode: "A",
            fundName: "Alpha",
            estimatedGrowth: 2.0,
            totalWeight: 1.0,
            components: [],
            timestamp: Date()
        )
        let b = FundValuation(
            fundCode: "B",
            fundName: "Beta",
            estimatedGrowth: 1.0,
            totalWeight: 1.0,
            components: [],
            timestamp: Date()
        )
        let c = FundValuation(
            fundCode: "C",
            fundName: "Gamma",
            estimatedGrowth: 3.0,
            totalWeight: 1.0,
            components: [],
            timestamp: Date()
        )
        vm.watchlist = [a, b, c]
        vm.watchlistItems = [
            WatchlistItem(id: "1", userId: "u", fundCode: "A", fundName: "Alpha", groupId: "g1", sortIndex: 1, createdAt: Date(), updatedAt: Date(), isDeleted: false),
            WatchlistItem(id: "2", userId: "u", fundCode: "B", fundName: "Beta", groupId: "g1", sortIndex: 0, createdAt: Date(), updatedAt: Date(), isDeleted: false),
            WatchlistItem(id: "3", userId: "u", fundCode: "C", fundName: "Gamma", groupId: nil, sortIndex: 2, createdAt: Date(), updatedAt: Date(), isDeleted: false)
        ]

        vm.viewMode = .group("g1")
        vm.sortOrder = .none
        #expect(vm.sortedWatchlist.map(\.fundCode) == ["B", "A"])

        vm.sortOrder = .highGrowthFirst
        #expect(vm.sortedWatchlist.map(\.fundCode) == ["A", "B"])
    }

    @MainActor
    @Test("基金详情基线: 初始状态")
    func fundDetailBaselineInitialState() async throws {
        let valuation = FundValuation(
            fundCode: "D",
            fundName: "Delta",
            estimatedGrowth: 1.23,
            totalWeight: 1.0,
            components: [],
            timestamp: Date()
        )
        let vm = FundDetailViewModel(valuation: valuation)

        #expect(vm.isLive == false)
        #expect(vm.liveGrowth == valuation.estimatedGrowth)
        #expect(vm.valuation.fundCode == "D")
    }

    @Test("市场状态: A股开市/午休/休市")
    func marketStatusCN() async throws {
        let open = makeDate(year: 2026, month: 3, day: 4, hour: 10, minute: 0, timeZoneId: "Asia/Shanghai")
        let lunch = makeDate(year: 2026, month: 3, day: 4, hour: 12, minute: 0, timeZoneId: "Asia/Shanghai")
        let closed = makeDate(year: 2026, month: 3, day: 7, hour: 10, minute: 0, timeZoneId: "Asia/Shanghai")

        #expect(MarketSessionStatusResolver.status(for: .cn, now: open) == .open)
        #expect(MarketSessionStatusResolver.status(for: .cn, now: lunch) == .lunchBreak)
        #expect(MarketSessionStatusResolver.status(for: .cn, now: closed) == .closed)
    }

    @Test("市场状态: QDII按美股时段")
    func marketStatusQDII() async throws {
        let valuation = FundValuation(
            fundCode: "968012",
            fundName: "Test QDII",
            estimatedGrowth: 0.1,
            totalWeight: 1.0,
            components: [],
            timestamp: Date(),
            isQdii: true
        )
        let open = makeDate(year: 2026, month: 3, day: 4, hour: 10, minute: 0, timeZoneId: "America/New_York")
        let closed = makeDate(year: 2026, month: 3, day: 4, hour: 17, minute: 0, timeZoneId: "America/New_York")

        #expect(MarketSessionStatusResolver.status(for: valuation, now: open) == .open)
        #expect(MarketSessionStatusResolver.status(for: valuation, now: closed) == .closed)
    }

    @Test("市场状态: 服务端字段优先于本地推断")
    func marketStatusServerPriority() async throws {
        let valuation = FundValuation(
            fundCode: "000001",
            fundName: "Server Status Test",
            estimatedGrowth: 0.1,
            totalWeight: 1.0,
            components: [],
            timestamp: Date(),
            marketStatus: "CLOSED"
        )
        let cnOpenTime = makeDate(year: 2026, month: 3, day: 4, hour: 10, minute: 0, timeZoneId: "Asia/Shanghai")
        #expect(MarketSessionStatusResolver.status(for: valuation, now: cnOpenTime) == .closed)
    }

    @Test("市场状态: market_status 解码")
    func marketStatusDecoding() async throws {
        let payload = """
        {
          "fund_code":"000001",
          "fund_name":"Decode Test",
          "estimated_growth":0.35,
          "total_weight":100.0,
          "components":[],
          "timestamp":"2026-03-01T12:00:00Z",
          "market_status":"OPEN"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let decoded = try decoder.decode(FundValuation.self, from: payload)

        #expect(decoded.marketStatus == "OPEN")
        #expect(MarketSessionStatusResolver.status(for: decoded) == .open)
    }

    private func makeDate(year: Int, month: Int, day: Int, hour: Int, minute: Int, timeZoneId: String) -> Date {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: timeZoneId) ?? TimeZone(secondsFromGMT: 0) ?? .current
        let components = DateComponents(
            timeZone: calendar.timeZone,
            year: year,
            month: month,
            day: day,
            hour: hour,
            minute: minute
        )
        return calendar.date(from: components) ?? Date(timeIntervalSince1970: 0)
    }

}
