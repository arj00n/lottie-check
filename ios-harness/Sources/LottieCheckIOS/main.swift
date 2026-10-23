import AppKit
import Lottie
import Metal
import QuartzCore

// usage: LottieCheckIOS <file.lottie|file.json> <out-dir> <frame...>
//
// Replays what lottie-react-native 7.3.5 does on iOS for a cached file:// source:
//   .lottie -> LottieAnimationView(dotLottieUrl:)        (DotLottieFile.loadedFrom(url:) + first animation)
//   .json   -> URLSession + JSONDecoder().decode(LottieAnimation.self)
// with renderMode AUTOMATIC, then composites each frame through CARenderer (Metal), like the device does.

let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1])
let outDir = URL(fileURLWithPath: args[2])
let frames = args.dropFirst(3).compactMap { Double($0) }
LottieLogger.shared = .printToConsole

let device = MTLCreateSystemDefaultDevice()!
let queue = device.makeCommandQueue()!

@MainActor
func snapshot(_ root: CALayer, size: CGSize, to file: URL) {
  let w = Int(size.width), h = Int(size.height)
  let desc = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .bgra8Unorm, width: w, height: h, mipmapped: false)
  desc.usage = [.renderTarget, .shaderRead]
  desc.storageMode = .managed
  let tex = device.makeTexture(descriptor: desc)!
  let renderer = CARenderer(mtlTexture: tex, options: [kCARendererMetalCommandQueue as String: queue])
  let host = CALayer()
  host.frame = CGRect(origin: .zero, size: size)
  host.backgroundColor = NSColor.white.cgColor
  host.isGeometryFlipped = true
  host.addSublayer(root)
  renderer.layer = host
  renderer.bounds = host.frame
  CATransaction.flush()
  renderer.beginFrame(atTime: CACurrentMediaTime(), timeStamp: nil)
  renderer.addUpdate(renderer.bounds)
  renderer.render()
  renderer.endFrame()
  let cb = queue.makeCommandBuffer()!
  let blit = cb.makeBlitCommandEncoder()!
  blit.synchronize(resource: tex)
  blit.endEncoding()
  cb.commit()
  cb.waitUntilCompleted()
  var bytes = [UInt8](repeating: 0, count: w * h * 4)
  tex.getBytes(&bytes, bytesPerRow: w * 4, from: MTLRegionMake2D(0, 0, w, h), mipmapLevel: 0)
  let srgb = CGColorSpace(name: CGColorSpace.sRGB)!
  let src = CGContext(data: &bytes, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: srgb,
                      bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)!
  // Metal readback is bottom-up
  let out = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: srgb,
                      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  out.translateBy(x: 0, y: CGFloat(h))
  out.scaleBy(x: 1, y: -1)
  out.draw(src.makeImage()!, in: CGRect(x: 0, y: 0, width: w, height: h))
  try! NSBitmapImageRep(cgImage: out.makeImage()!).representation(using: .png, properties: [:])!.write(to: file)
  root.removeFromSuperlayer()
}

func fail(_ message: String) -> Never {
  print("RESULT FAIL \(message)")
  exit(2)
}

Task { @MainActor in
  let config = LottieConfiguration(renderingEngine: .automatic)
  let layer: LottieAnimationLayer
  if url.pathExtension.lowercased() == "lottie" {
    let file: DotLottieFile
    do { file = try await DotLottieFile.loadedFrom(url: url) } catch { fail("dotLottie load: \(error)") }
    layer = LottieAnimationLayer(dotLottie: file, configuration: config)
  } else {
    let animation: LottieAnimation
    do { animation = try JSONDecoder().decode(LottieAnimation.self, from: Data(contentsOf: url)) } catch { fail("JSON decode: \(error)") }
    layer = LottieAnimationLayer(animation: animation, configuration: config)
  }
  guard let animation = layer.animation else { fail("no animation in file") }
  let size = animation.size
  layer.frame = CGRect(origin: .zero, size: size)
  layer.display()
  print("INFO size=\(Int(size.width))x\(Int(size.height)) frames=\(Int(animation.startFrame))-\(Int(animation.endFrame)) fps=\(animation.framerate) engine=\(layer.currentRenderingEngine.map { "\($0)" } ?? "?")")
  for f in frames {
    layer.currentFrame = f
    layer.forceDisplayUpdate()
    layer.setNeedsLayout()
    layer.layoutIfNeeded()
    layer.animationLayer?.position = CGPoint(x: size.width / 2, y: size.height / 2)
    snapshot(layer, size: size, to: outDir.appendingPathComponent("ios-f\(Int(f)).png"))
  }
  print("RESULT OK")
  exit(0)
}
RunLoop.main.run()
