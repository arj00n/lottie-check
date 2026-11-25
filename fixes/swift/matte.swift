import AppKit
// matte <onBlack.png> <onWhite.png> <out.png>: recover premultiplied RGBA from two opaque renders; prints alpha bbox
let a = CommandLine.arguments
func load(_ p: String) -> (Int, Int, [UInt8]) {
  let img = NSBitmapImageRep(data: try! Data(contentsOf: URL(fileURLWithPath: p)))!.cgImage!
  let w = img.width, h = img.height; var px = [UInt8](repeating: 0, count: w * h * 4)
  let ctx = CGContext(data: &px, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h)); return (w, h, px)
}
let (w, h, k) = load(a[1]); let (_, _, wh) = load(a[2])
var out = [UInt8](repeating: 0, count: w * h * 4)
var mx = w, my = h, Mx = -1, My = -1
for i in 0..<(w * h) {
  var al = 0.0
  for c in 0..<3 { al += 255.0 - (Double(wh[i * 4 + c]) - Double(k[i * 4 + c])) }
  al = max(0, min(255, al / 3)); let A = UInt8(al.rounded())
  out[i * 4 + 3] = A
  for c in 0..<3 { out[i * 4 + c] = UInt8(min(Double(k[i * 4 + c]), al).rounded()) }
  if A > 1 { let x = i % w, y = i / w; mx = min(mx, x); my = min(my, y); Mx = max(Mx, x); My = max(My, y) }
}
let ctx = CGContext(data: &out, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
let full = ctx.makeImage()!
let crop = full.cropping(to: CGRect(x: mx, y: my, width: Mx - mx + 1, height: My - my + 1))!
try! NSBitmapImageRep(cgImage: crop).representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[3]))
print("BBOX \(mx) \(my) \(Mx - mx + 1) \(My - my + 1)")
