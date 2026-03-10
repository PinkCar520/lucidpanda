// mobile/ios/Packages/AlphaDesign/Sources/AlphaDesign/Extensions/Color+Semantic.swift

import SwiftUI

public extension Color {
    /// Semantic colors for AlphaSignal (Institutional Trust Scheme)
    struct Alpha {
        // MARK: - Brand & Interactive Structure
        
        /// Primary brand color (Cobalt Blue). Used for core actions, active states.
        public static let primary = Color(hex: "#2563EB")
        
        // Use a dynamic property to resolve Light/Dark mode backgrounds
        public static var background: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#0F172A") // Deep Navy
                    : UIColor(hex: "#F8FAFC") // Very light gray
            })
        }
        
        /// Surface color (Cards, Modals).
        public static var surface: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#1E293B") // Slightly lighter Navy
                    : UIColor(hex: "#FFFFFF") // Pure White
            })
        }
        
        /// Borders and separators.
        public static var separator: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#334155")
                    : UIColor(hex: "#E2E8F0")
            })
        }
        
        // MARK: - Financial Semantics
        
        /// Up / Bullish (Emerald Green)
        public static let up = Color(hex: "#10B981")
        
        /// Down / Bearish (Rose Red)
        public static let down = Color(hex: "#EF4444")
        
        /// Neutral / Flat
        public static let neutral = Color(hex: "#64748B")
        
        // MARK: - Typography
        
        /// Primary Text
        public static var textPrimary: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#F8FAFC") // Off-white for dark mode
                    : UIColor(hex: "#0F172A") // Rich Navy-Black for light mode
            })
        }
        
        /// Secondary Text
        public static var textSecondary: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#94A3B8")
                    : UIColor(hex: "#64748B")
            })
        }
    }
}
