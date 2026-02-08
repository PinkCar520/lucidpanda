// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AlphaCore",
    platforms: [.iOS(.v18)],
    products: [
        .library(name: "AlphaCore", targets: ["AlphaCore"]),
    ],
    targets: [
        .target(name: "AlphaCore", path: "Sources/AlphaCore"),
    ]
)