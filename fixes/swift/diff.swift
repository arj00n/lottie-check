import AppKit
// diff <a.png> <b.png>: mean abs channel difference and share of pixels off by >40 in any channel
func load(_ p: String) -> (Int, Int, [UInt8]) {
  let img = NSBitmapImageRep(data: try! Data(contentsOf: URL(fileURLWithPath: p)))!.cgImage!
  let w = img.width, h = img.height; var px = [UInt8](repeating: 0, count: w * h * 4)
  let ctx = CGContext(data: &px, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h)); return (w, h, px)
}
let a = CommandLine.arguments
let (w, h, x) = load(a[1]); let (w2, h2, y) = load(a[2])
guard w == w2 && h == h2 else { print("size differs \(w)x\(h) vs \(w2)x\(h2)"); exit(1) }
var sum = 0.0, off = 0
for i in 0..<(w * h) {
  var m = 0
  for c in 0..<4 { let d = abs(Int(x[i * 4 + c]) - Int(y[i * 4 + c])); sum += Double(d); m = max(m, d) }
  if m > 40 { off += 1 }
}
print(String(format: "mean %.2f/255, pixels off by >40: %.2f%%", sum / Double(w * h * 4), Double(off) / Double(w * h) * 100))
