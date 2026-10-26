package `in`.justswish.lottiecheck

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Picture
import android.widget.ImageView
import androidx.test.core.app.ApplicationProvider
import com.airbnb.lottie.LottieComposition
import com.airbnb.lottie.LottieCompositionFactory
import com.airbnb.lottie.LottieDrawable
import java.io.File
import java.io.FileInputStream
import java.util.zip.ZipInputStream
import kotlin.math.roundToInt
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/**
 * Emulator-free Android check. Parses with the same lottie-android 6.5.2 entry points Swish reaches
 * through setAnimationFromUrl (fromZipStreamSync for .lottie, fromJsonInputStreamSync for .json) and
 * renders with Robolectric's native graphics (real Skia). Writes one "RESULT" line per file to
 * <lottie.out>/android-results.txt.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35])
class RobolectricCheck {
  @Test
  fun check() {
    // lottie.list: one "<path>\t<frame,frame,...>" per line
    val entries = File(System.getProperty("lottie.list").orEmpty()).readLines().filter { it.isNotBlank() }
    val outRoot = File(System.getProperty("lottie.out").orEmpty())
    val results = File(outRoot, "android-results.txt").apply { writeText("") }
    val bench = System.getProperty("lottie.bench") == "true"
    val context = ApplicationProvider.getApplicationContext<android.content.Context>()

    for (entry in entries) {
      val path = entry.substringBefore("\t")
      val frames = entry.substringAfter("\t", "").split(",").mapNotNull { it.trim().toIntOrNull() }
      val file = File(path)
      val result = if (file.name.endsWith(".lottie")) {
        LottieCompositionFactory.fromZipStreamSync(context, ZipInputStream(FileInputStream(file)), path)
      } else {
        LottieCompositionFactory.fromJsonInputStreamSync(FileInputStream(file), path)
      }
      val composition = result.value
      if (composition == null) {
        results.appendText("RESULT FAIL $path :: ${result.exception?.javaClass?.simpleName}: ${result.exception?.message}\n")
        continue
      }
      val density = context.resources.displayMetrics.density
      val w = (composition.bounds.width() / density).roundToInt()
      val h = (composition.bounds.height() / density).roundToInt()
      val out = File(outRoot, file.name).apply { mkdirs() }
      try {
      val drawable = LottieDrawable().apply {
        setComposition(composition)
        setBounds(0, 0, w, h)
      }
      // Hosted in a view like LottieAnimationView: lottie-android decodes base64 images embedded in a
      // .json lazily through the drawable's view, and silently skips them without one (.lottie images
      // are decoded up front, so they render either way). Drawables hold their view weakly, so `host`
      // must stay reachable until the last draw.
      val host = ImageView(context).apply { setImageDrawable(drawable) }
      for (f in frames) {
        val bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)
        drawable.frame = f
        drawable.draw(canvas)
        File(out, "android-f$f.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
      }
      val perf = if (bench) " :: draw cost per frame: ${bench(composition, drawable, w, h)}" else ""
      val warnings = composition.warnings.joinToString("") { " :: WARNING $it" }
      java.lang.ref.Reference.reachabilityFence(host)
      results.appendText("RESULT OK $path :: size=${w}x$h frames=${composition.startFrame.toInt()}-${composition.endFrame.toInt()} fps=${composition.frameRate}$perf$warnings\n")
      } catch (e: Throwable) {
        results.appendText("RESULT FAIL $path :: render crashed: ${e.javaClass.simpleName}: ${e.message}\n")
      }
    }
  }

  /** Same measure as the app's bench: record every frame into a Picture, 3 warm passes. */
  private fun bench(composition: LottieComposition, drawable: LottieDrawable, w: Int, h: Int): String {
    val times = mutableListOf<Double>()
    repeat(4) { pass ->
      for (f in composition.startFrame.toInt() until composition.endFrame.toInt()) {
        drawable.frame = f
        val picture = Picture()
        val start = System.nanoTime()
        drawable.draw(picture.beginRecording(w, h))
        picture.endRecording()
        if (pass > 0) times += (System.nanoTime() - start) / 1e6
      }
    }
    times.sort()
    fun pct(p: Double) = "%.2f".format(times[((times.size - 1) * p).roundToInt()])
    return "p50=${pct(0.5)}ms p90=${pct(0.9)}ms p99=${pct(0.99)}ms max=${pct(1.0)}ms"
  }
}
