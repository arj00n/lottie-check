plugins {
  id("com.android.application")
  id("org.jetbrains.kotlin.android")
}

android {
  namespace = "in.justswish.lottiecheck"
  compileSdk = 35
  defaultConfig {
    applicationId = "in.justswish.lottiecheck"
    minSdk = 24
    targetSdk = 35
    versionCode = 1
    versionName = "1"
  }
  compileOptions {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
  }
  kotlinOptions { jvmTarget = "17" }
  testOptions { unitTests.isIncludeAndroidResources = true }
}

// `./gradlew :app:testDebugUnitTest -PlottieList=files.tsv -PlottieOut=dir -PlottieBench=true`
// runs RobolectricCheck: lottie-android parsing + rendering in a plain JVM, no emulator.
tasks.withType<Test>().configureEach {
  systemProperty("lottie.list", project.findProperty("lottieList") ?: "")
  systemProperty("lottie.out", project.findProperty("lottieOut") ?: "")
  systemProperty("lottie.bench", project.findProperty("lottieBench") ?: "false")
  outputs.upToDateWhen { false }
  testLogging { showStandardStreams = true }
}

dependencies {
  // Swish resolves com.airbnb.android:lottie to 6.5.2 (app pins 6.5.0, lottie-react-native 7.3.5 pulls 6.5.2).
  implementation("com.airbnb.android:lottie:6.5.2")
  testImplementation("junit:junit:4.13.2")
  testImplementation("org.robolectric:robolectric:4.17")
  testImplementation("androidx.test:core:1.6.1")
}
