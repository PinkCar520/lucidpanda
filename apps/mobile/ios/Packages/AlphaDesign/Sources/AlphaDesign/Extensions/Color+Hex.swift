// mobile/ios/Packages/AlphaDesign/Sources/AlphaDesign/Extensions/Color+Hex.swift

import SwiftUI

extension Color {
    /// Initialize Color from hex string (e.g. "#007AFF" or "007AFF")
    public init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
    
    /// Initialize Color from hex string (optional)
    public init?(hex: String?) {
        guard let hex = hex else { return nil }
        self.init(hex: hex)
    }
    
    /// Convert Color to hex string
    public var hexString: String? {
        guard let components = UIColor(self).cgColor.components, components.count >= 3 else {
            return nil
        }
        
        let r = components[0]
        let g = components.count >= 2 ? components[1] : 0
        let b = components.count >= 3 ? components[2] : 0
        let a = components.count >= 4 ? components[3] : 1
        
        return String(format: "#%02lX%02lX%02lX%02lX",
                      lroundf(Float(r * 255)),
                      lroundf(Float(g * 255)),
                      lroundf(Float(b * 255)),
                      lroundf(Float(a * 255)))
    }
}

// MARK: - UIColor extension

extension UIColor {
    convenience init(hex: String) {
        let color = Color(hex: hex)
        self.init(color)
    }
}
