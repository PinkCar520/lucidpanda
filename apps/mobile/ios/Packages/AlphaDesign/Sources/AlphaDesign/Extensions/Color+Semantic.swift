// mobile/ios/Packages/AlphaDesign/Sources/AlphaDesign/Extensions/Color+Semantic.swift

import SwiftUI

public extension Color {
    /// Semantic colors for LucidPanda (Institutional Trust Scheme)
    struct Alpha {
        // MARK: - Brand & Interactive Structure
        
        /// Brand accent color (#B35919) - Gold Quant Orange
        public static let brand = Color(hex: "#B35919")
        
        /// Primary brand color.
        public static let primary = brand
        
        // MARK: - Taupe Scale (Tailwind Stone/Taupe equivalent)
        public static let taupe50  = Color(hex: "#F5F5F4")
        public static let taupe100 = Color(hex: "#E7E5E4")
        public static let taupe200 = Color(hex: "#D6D3D1")
        public static let taupe300 = Color(hex: "#A8A29E")
        public static let taupe400 = Color(hex: "#78716C")
        public static let taupe500 = Color(hex: "#57534E")
        public static let taupe600 = Color(hex: "#44403C")
        public static let taupe700 = Color(hex: "#292524")
        public static let taupe800 = Color(hex: "#1C1917")
        public static let taupe900 = Color(hex: "#0C0A09")
        
        // MARK: - Semantic Mappings
        
        /// App Background (#121212 in Design)
        public static var background: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#121212")
                    : UIColor(hex: "#F5F5F4")
            })
        }
        
        /// Surface color (Cards, Modals) (#1E1E1E in Design)
        public static var surface: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#1E1E1E")
                    : UIColor(hex: "#FFFFFF")
            })
        }
        
        /// Borders and separators.
        public static var separator: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#292524")
                    : UIColor(hex: "#E7E5E4")
            })
        }
        
        // MARK: - Financial Semantics
        
        /// Up / Bullish (Emerald Green)
        public static let up = Color(hex: "#10B981")
        
        /// Down / Bearish (Rose Red)
        public static let down = Color(hex: "#EF4444")
        
        /// Neutral / Flat
        public static let neutral = Color(hex: "#78716C")
        
        // MARK: - Typography
        
        /// Primary Text
        public static var textPrimary: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#E7E5E4") // Taupe 100
                    : UIColor(hex: "#0C0A09") // Taupe 900
            })
        }
        
        /// Secondary Text
        public static var textSecondary: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#A8A29E") // Taupe 300
                    : UIColor(hex: "#57534E") // Taupe 500
            })
        }
    }
}
