import AppKit
import Lottie
import Metal
import QuartzCore

// usage: Rasterize <in.json>... : renders frame 0 of each on a transparent canvas with lottie-ios,
// crops to the alpha bounding box, writes <in>.png and prints "BBOX <in> x y w h".
let device = MTLCreateSystemDefaultDevice()!
let queue = device.makeCommandQueue()!

@MainActor
func rasterize(_ path: String) throws {
  let animation = try JSONDecoder().decode(LottieAnimation.self, from: Data(contentsOf: URL(fileURLWithPath: path)))
  let layer = LottieAnimationLayer(animation: animation, configuration: LottieConfiguration(renderingEngine: .automatic))
  let size = animation.size
  let w = Int(size.width), h = Int(size.height)
  layer.frame = CGRect(origin: .zero, size: size)
  layer.display()
  layer.currentFrame = 0
  layer.forceDisplayUpdate()
  layer.layoutIfNeeded()
  layer.animationLayer?.position = CGPoint(x: size.width / 2, y: size.height / 2)

  let desc = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .bgra8Unorm, width: w, height: h, mipmapped: false)
  desc.usage = [.renderTarget, .shaderRead]
  desc.storageMode = .managed
  let tex = device.makeTexture(descriptor: desc)!
  var zero = [UInt8](repeating: 0, count: w * h * 4)
  tex.replace(region: MTLRegionMake2D(0, 0, w, h), mipmapLevel: 0, withBytes: &zero, bytesPerRow: w * 4)
  let renderer = CARenderer(mtlTexture: tex, options: [kCARendererMetalCommandQueue as String: queue])
  let host = CALayer()
  host.frame = layer.frame
  host.isGeometryFlipped = true
  host.addSublayer(layer)
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

  var px = [UInt8](repeating: 0, count: w * h * 4)
  tex.getBytes(&px, bytesPerRow: w * 4, from: MTLRegionMake2D(0, 0, w, h), mipmapLevel: 0)
  // texture rows are bottom-up: flip to top-down while finding the alpha bbox
  var rows = [UInt8](repeating: 0, count: w * h * 4)
  var minX = w, minY = h, maxX = -1, maxY = -1
  for y in 0..<h {
    let src = (h - 1 - y) * w * 4
    for x in 0..<w {
      let i = src + x * 4, o = (y * w + x) * 4
      rows[o] = px[i]; rows[o + 1] = px[i + 1]; rows[o + 2] = px[i + 2]; rows[o + 3] = px[i + 3]
      if px[i + 3] > 0 { minX = min(minX, x); maxX = max(maxX, x); minY = min(minY, y); maxY = max(maxY, y) }
    }
  }
  guard maxX >= 0 else { print("EMPTY \(path)"); return }
  if minX == 0 || minY == 0 || maxX == w - 1 || maxY == h - 1 { print("WARN \(path) touches canvas edge") }
  let srgb = CGColorSpace(name: CGColorSpace.sRGB)!
  let ctx = CGContext(data: &rows, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: srgb,
                      bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)!
  let crop = ctx.makeImage()!.cropping(to: CGRect(x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1))!
  try NSBitmapImageRep(cgImage: crop).representation(using: .png, properties: [:])!
    .write(to: URL(fileURLWithPath: path.replacingOccurrences(of: ".json", with: ".png")))
  print("BBOX \(path) \(minX) \(minY) \(maxX - minX + 1) \(maxY - minY + 1)")
}

Task { @MainActor in
  for path in CommandLine.arguments.dropFirst() {
    do { try rasterize(path) } catch { print("FAIL \(path) \(error)") }
  }
  exit(0)
}
RunLoop.main.run()
