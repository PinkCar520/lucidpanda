// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AlphaData",
    platforms: [.iOS(.v18)],
    products: [
        .library(name: "AlphaData", targets: ["AlphaData"]),
    ],
    dependencies: [
        .package(path: "../AlphaCore")
    ],
    targets: [
        .target(
            name: "AlphaData",
            dependencies: ["AlphaCore"],
            path: "Sources/AlphaData"
        ),
    ]
)