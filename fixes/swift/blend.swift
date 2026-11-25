import AppKit
// blend <backdrop.png (full canvas, opaque)> <layer.png (cropped)> <x> <y> <mode> <out.png>
// Writes the layer's alpha with colour B(backdrop, layer), so normal-compositing it over the backdrop reproduces
// the blend. Modes: multiply, screen, overlay, darken, lighten, hardlight (W3C separable formulas, sRGB).
let a = CommandLine.arguments
func load(_ p: String) -> (Int, Int, [UInt8]) {
  let img = NSBitmapImageRep(data: try! Data(contentsOf: URL(fileURLWithPath: p)))!.cgImage!
  let w = img.width, h = img.height; var px = [UInt8](repeating: 0, count: w * h * 4)
  let ctx = CGContext(data: &px, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h)); return (w, h, px)
}
func hard(_ b: Double, _ s: Double) -> Double { s <= 0.5 ? b * 2 * s : b + (2 * s - 1) - b * (2 * s - 1) }
let fn: (Double, Double) -> Double
switch a[5] {
case "multiply": fn = { b, s in b * s }
case "screen": fn = { b, s in b + s - b * s }
case "overlay": fn = { b, s in hard(s, b) }
case "darken": fn = { b, s in min(b, s) }
case "lighten": fn = { b, s in max(b, s) }
case "hardlight": fn = hard
default: print("unknown mode \(a[5])"); exit(2)
}
let (bw, _, bd) = load(a[1]); let (lw, lh, ly) = load(a[2]); let ox = Int(a[3])!, oy = Int(a[4])!
var out = [UInt8](repeating: 0, count: lw * lh * 4)
for y in 0..<lh { for x in 0..<lw {
  let i = (y * lw + x) * 4, al = Double(ly[i + 3]) / 255; if al == 0 { continue }
  let j = ((y + oy) * bw + (x + ox)) * 4
  for c in 0..<3 {
    let s = min(1, Double(ly[i + c]) / 255 / al), b = Double(bd[j + c]) / 255
    out[i + c] = UInt8((fn(b, s) * al * 255).rounded())
  }
  out[i + 3] = ly[i + 3]
} }
let ctx = CGContext(data: &out, width: lw, height: lh, bitsPerComponent: 8, bytesPerRow: lw * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
try! NSBitmapImageRep(cgImage: ctx.makeImage()!).representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[6]))
