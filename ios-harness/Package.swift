// swift-tools-version:5.9
import PackageDescription

// Pinned to the lottie-ios that Swish ships (lottie-react-native 7.3.5 -> lottie-ios 4.5.0).
let package = Package(
  name: "LottieCheckIOS",
  platforms: [.macOS(.v13)],
  dependencies: [.package(url: "https://github.com/airbnb/lottie-spm.git", exact: "4.5.0")],
  targets: [
    .executableTarget(name: "LottieCheckIOS", dependencies: [.product(name: "Lottie", package: "lottie-spm")]),
    // Renders a Lottie JSON's frame 0 to a transparent PNG cropped to its content (used to flatten groups).
    .executableTarget(name: "Rasterize", dependencies: [.product(name: "Lottie", package: "lottie-spm")]),
  ]
)
