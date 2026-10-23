package `in`.justswish.lottiecheck

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Picture
import android.os.Bundle
import android.util.Log
import android.widget.ImageView
import com.airbnb.lottie.LottieAnimationView
import com.airbnb.lottie.LottieComposition
import com.airbnb.lottie.LottieDrawable
import kotlin.math.roundToInt

private const val TAG = "LOTTIE_CHECK"

/**
 * Driven by `lottie-check` over adb:
 *   --es url <http url>   load like Swish on Android (lottie-react-native 7.3.5 -> setAnimationFromUrl)
 *   --ei frame <n>        pause on frame n, then log "FRAME n"
 *   --ez play true        resume looping playback
 *   --ez bench true       time per-frame draw work, then log "BENCH ..."
 */
class MainActivity : Activity() {
  private lateinit var view: LottieAnimationView

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    view = LottieAnimationView(this).apply {
      scaleType = ImageView.ScaleType.FIT_CENTER
      setBackgroundColor(Color.WHITE)
      repeatCount = LottieDrawable.INFINITE
      setFailureListener { e -> Log.i(TAG, "FAILED ${e.javaClass.simpleName}: ${e.message}") }
      addLottieOnCompositionLoadedListener { c ->
        c.warnings.forEach { Log.i(TAG, "WARNING $it") }
        val density = resources.displayMetrics.density
        Log.i(TAG, "LOADED size=${(c.bounds.width() / density).roundToInt()}x${(c.bounds.height() / density).roundToInt()} frames=${c.startFrame.toInt()}-${c.endFrame.toInt()} fps=${c.frameRate}")
      }
    }
    setContentView(view)
    handle(intent)
  }

  override fun onNewIntent(intent: Intent) {
    super.onNewIntent(intent)
    setIntent(intent)
    handle(intent)
  }

  private fun handle(intent: Intent) {
    intent.getStringExtra("url")?.let { url ->
      // Same branching as LottieAnimationViewPropertyManager.commitChanges() in lottie-react-native 7.3.5
      if (url.contains(".lottie")) view.setAnimationFromUrl(url) else view.setAnimationFromUrl(url, url.hashCode().toString())
      view.playAnimation()
    }
    if (intent.hasExtra("frame")) {
      val frame = intent.getIntExtra("frame", 0)
      view.pauseAnimation()
      view.frame = frame
      view.postDelayed({ Log.i(TAG, "FRAME $frame") }, 400)
    }
    if (intent.getBooleanExtra("play", false)) view.resumeAnimation()
    if (intent.getBooleanExtra("bench", false)) view.composition?.let { bench(it) }
  }

  /**
   * Times lottie-android's per-frame work: every frame is recorded into a Picture (a display list),
   * which is what the UI thread does each frame on a hardware-accelerated phone. GPU time is excluded,
   * so the numbers are stable on the emulator and comparable between files. Logs "BENCH ...".
   */
  private fun bench(composition: LottieComposition) {
    val width = resources.displayMetrics.widthPixels
    val height = (width * composition.bounds.height().toFloat() / composition.bounds.width()).roundToInt()
    Thread {
      val drawable = LottieDrawable().apply {
        setComposition(composition)
        setBounds(0, 0, width, height)
      }
      val frames = composition.startFrame.toInt() until composition.endFrame.toInt()
      val times = mutableListOf<Double>()
      repeat(4) { pass ->
        for (f in frames) {
          drawable.frame = f
          val picture = Picture()
          val start = System.nanoTime()
          drawable.draw(picture.beginRecording(width, height))
          picture.endRecording()
          if (pass > 0) times += (System.nanoTime() - start) / 1e6 // pass 0 warms caches
        }
      }
      times.sort()
      fun pct(p: Double) = "%.2f".format(times[((times.size - 1) * p).roundToInt()])
      Log.i(TAG, "BENCH frames=${times.size} p50=${pct(0.5)}ms p90=${pct(0.9)}ms p99=${pct(0.99)}ms max=${pct(1.0)}ms")
    }.start()
  }
}
