// mobile/ios/Packages/AlphaDesign/Sources/AlphaDesign/Extensions/Color+Semantic.swift

import SwiftUI

public extension Color {
    /// Semantic colors for LucidPanda (Institutional Trust Scheme)
    struct Alpha {
        // MARK: - Brand & Interactive Structure
        
        /// Brand accent color (#b35919) - Editorial Gold
        public static var brand: Color {
            Color(hex: "#b35919")
        }
        
        public static var primary: Color { brand }
        
        /// Secondary brand color (#D4A373)
        public static var primaryContainer: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#1E3A8A")
                    : UIColor(hex: "#D4A373")
            })
        }
        
        // MARK: - Surface Hierarchy (The Quiet Editorial)
        
        public static var surface: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#1E1E1E")
                    : UIColor(hex: "#ffffff") // card / white
            })
        }
        
        public static var surfaceContainerLow: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#121212")
                    : UIColor(hex: "#f4f3f1") // surface-container-low
            })
        }
        
        public static var surfaceContainerLowest: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#1E1E1E")
                    : UIColor(hex: "#FFFFFF") // surface-container-lowest
            })
        }
        
        public static var surfaceDim: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#0C0A09")
                    : UIColor(hex: "#DBDAD7") // surface-dim
            })
        }
        
        /// Dynamic Taupe for metadata and secondary headers
        public static var taupe: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#8D827A") // Taupe for dark
                    : UIColor(hex: "#6b645f") // Darkened Taupe for light
            })
        }
        
        // MARK: - Foundational Tokens (Taupe Scale)
        
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
        
        public static var background: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#121212")
                    : UIColor(hex: "#f8f8f7") // Off-white
            })
        }
        
        public static var separator: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#292524")
                    : UIColor(hex: "#E5E7EB") // gray-200
            })
        }
        
        // MARK: - Financial Semantics
        
        /// Up / Bullish (Emerald Green)
        public static var up: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#10B981")
                    : UIColor(hex: "#059669") // Slightly deeper green for light mode
            })
        }
        
        /// Down / Bearish (Rose Red)
        public static var down: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#EF4444")
                    : UIColor(hex: "#DC2626") // Slightly deeper red for light mode
            })
        }
        
        /// Neutral / Flat
        public static let neutral = Color(hex: "#78716C")
        
        // MARK: - Typography
        
        public static var textPrimary: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#E7E5E4")
                    : UIColor(hex: "#1a1a1a") // Primary text
            })
        }
        
        public static var textSecondary: Color {
            Color(UIColor { traitCollection in
                traitCollection.userInterfaceStyle == .dark
                    ? UIColor(hex: "#A8A29E")
                    : UIColor(hex: "#4b5563") // gray-600
            })
        }
    }
}
