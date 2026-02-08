// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AlphaDesign",
    platforms: [.iOS(.v18)],
    products: [
        .library(name: "AlphaDesign", targets: ["AlphaDesign"]),
    ],
    dependencies: [
        .package(path: "../AlphaData")
    ],
    targets: [
        .target(
            name: "AlphaDesign",
            dependencies: ["AlphaData"],
            path: "Sources/AlphaDesign"
        ),
    ]
)
