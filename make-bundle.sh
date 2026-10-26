#!/bin/zsh
# Build the prebuilt lottie-check bundle: dist/lottie-check-macos.zip
#
# Teammates unzip it and run ./install.sh. They need no Xcode, Homebrew, Gradle or Android SDK:
#   bin/       iOS checker + Rasterize (universal arm64/x86_64, macOS 13+) and Lottie.framework 4.5.0
#   android/   Robolectric check: jars, compiled classes, resources (runs on plain java)
#   jre/       trimmed Java 17 runtime for Apple Silicon (Intel Macs use an installed Java 17+)
# Android's runtime jar (200 MB, Maven Central) is downloaded by install.sh to ~/.lottie-check and
# checked against android/android-all.txt, so the zip stays small.
#
# Needs this repo's dev setup: Xcode, Homebrew openjdk@17 and android-commandlinetools.
set -euo pipefail

DIR=${0:A:h}
BREW=$(brew --prefix)
export JAVA_HOME="$BREW/opt/openjdk@17"
OUT="$DIR/dist/lottie-check"
ANDROID_ALL_VERSION="15-robolectric-13954326-i7"
ANDROID_ALL_JAR="android-all-instrumented-$ANDROID_ALL_VERSION.jar"
ANDROID_ALL_URL="https://repo1.maven.org/maven2/org/robolectric/android-all-instrumented/$ANDROID_ALL_VERSION/$ANDROID_ALL_JAR"

step() { print -P "\n%B==> $1%b" }

rm -rf "$DIR/dist"
mkdir -p "$OUT/bin" "$OUT/android/lib" "$OUT/android/classes" "$OUT/android/res/assets" \
  "$OUT/android/config/com/android/tools"

step "iOS checker (universal)"
(cd "$DIR/ios-harness" && swift build -c release --arch arm64 --arch x86_64 -q 2>&1 | grep -v -E "keychain|x86_64 architecture is deprecated" || true)
PRODUCTS=$(cd "$DIR/ios-harness" && swift build -c release --arch arm64 --arch x86_64 --show-bin-path)
cp "$PRODUCTS/LottieCheckIOS" "$PRODUCTS/Rasterize" "$OUT/bin/"
ditto "$PRODUCTS/Lottie.framework" "$OUT/bin/Lottie.framework"   # ditto keeps the framework's symlinks

step "Android checker (Robolectric, no Gradle at runtime)"
echo "sdk.dir=$BREW/share/android-commandlinetools" > "$DIR/android/local.properties"
CLASSPATH_FILES=("${(@f)$(cd "$DIR/android" && ./gradlew :app:printCheckerClasspath -q | grep '^CP ' | cut -c4-)}")
A="$DIR/android/app/build/intermediates"
cp "$A/apk_for_local_test/debugUnitTest/packageDebugUnitTestForUnitTest/apk-for-local-test.ap_" "$OUT/android/res/"
cp "$A/packaged_manifests/debug/processDebugManifestForPackage/AndroidManifest.xml" "$OUT/android/res/"
cat > "$OUT/android/config/com/android/tools/test_config.properties" <<'EOF'
android_merged_assets=res/assets
android_resource_apk=res/apk-for-local-test.ap_
android_custom_package=in.justswish.lottiecheck
android_merged_manifest=res/AndroidManifest.xml
EOF
entries=("config")
i=0
for f in $CLASSPATH_FILES; do
  i=$((i + 1))
  [[ $f == *unit_test_config_directory* ]] && continue   # replaced by config/ above (relative paths)
  if [[ -d $f ]]; then
    [[ -z $(ls -A "$f" 2>/dev/null) ]] && continue
    dest="classes/$(printf %03d $i)"
    mkdir -p "$OUT/android/$dest" && cp -R "$f/" "$OUT/android/$dest/"
  elif [[ -f $f ]]; then
    dest="lib/$(printf %03d $i)-${f:t}"
    if [[ ${f:t} == nativeruntime-dist-compat-*.jar ]]; then
      # Robolectric's native graphics for every OS (246 MB): keep macOS libraries and non-CJK fonts
      tmp=$(mktemp -d)
      (cd "$tmp" && unzip -q "$f" && rm -rf native/linux native/windows fonts/NotoSansCJK-* && zip -q -r -X "$OUT/android/$dest" .)
      rm -rf "$tmp"
    else
      cp "$f" "$OUT/android/$dest"
    fi
  else
    continue
  fi
  entries+=("$dest")
done
print -l $entries > "$OUT/android/classpath.txt"
ANDROID_ALL_LOCAL=$(find ~/.m2/repository/org/robolectric/android-all-instrumented -name "$ANDROID_ALL_JAR" | head -1)
print "$ANDROID_ALL_URL $(shasum -a 256 "$ANDROID_ALL_LOCAL" | cut -d' ' -f1)" > "$OUT/android/android-all.txt"

step "Java 17 runtime (Apple Silicon)"
"$JAVA_HOME/bin/jlink" --add-modules java.se,jdk.unsupported,jdk.zipfs,jdk.crypto.ec,jdk.localedata \
  --strip-debug --no-man-pages --no-header-files --compress=2 --output "$OUT/jre" 2>/dev/null

step "Scripts"
cp "$DIR/lottie-check" "$DIR/inbox-run" "$DIR/install.sh" "$DIR/uninstall.sh" "$DIR/README.md" "$OUT/"
cp -R "$DIR/macos" "$DIR/claude-skill" "$DIR/fixes" "$DIR/selftest" "$OUT/"
git -C "$DIR" describe --always --dirty > "$OUT/VERSION"

step "Zip"
# --norsrc/--noextattr: no ._ metadata files in the zip
(cd "$DIR/dist" && ditto -c -k --norsrc --noextattr --noqtn --keepParent lottie-check lottie-check-macos.zip)
du -sh "$OUT" "$DIR/dist/lottie-check-macos.zip"
