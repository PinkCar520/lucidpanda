// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/FundSearchModels.swift
import Foundation

public struct FundSearchResult: Codable, Identifiable {
    public var id: String { code }
    public let code: String
    public let name: String
    public let type: String?
    public let company: String?
    
    public init(code: String, name: String, type: String?, company: String?) {
        self.code = code
        self.name = name
        self.type = type
        self.company = company
    }
}
