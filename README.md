# lottie-check

Test `.lottie` / Lottie `.json` files against the players the Swish app ships, before uploading them.

## Install

### Prebuilt bundle (recommended, about 1 minute)

Unzip `lottie-check-macos.zip` anywhere and run:

```bash
lottie-check/install.sh
```

Needs macOS 13+ and nothing else on Apple Silicon. Intel Macs also need Java 17+; the installer gets it via Homebrew if it's there.

The installer:

1. Downloads Android's 200 MB runtime from Maven Central to `~/.lottie-check`, once, and verifies its checksum.
2. Self-tests on two lotties it generates: one valid, one broken. Both checkers must agree.
3. Adds the Finder Quick Action. Finder restarts once.

### From source (to change the tool)

Needs [Homebrew](https://brew.sh) and Xcode Command Line Tools. Clone this repo and run `./install.sh`. It installs Java 17 and the Android SDK via Homebrew (you may be asked to accept Google's SDK licence) and builds both checkers. Only a source checkout can use `--emulator`.

To build the bundle, run `./make-bundle.sh`. It writes `dist/lottie-check-macos.zip` (~145 MB) containing:

- a universal iOS checker (macOS 13+)
- the Robolectric check with its jars, running on plain `java`
- a trimmed Java 17 runtime for Apple Silicon

### Options (both)

- `--with-inbox` also watches `~/Lotties/inbox`.
- `--with-inbox --autofix` also lets [Claude Code](https://claude.com/claude-code) try to fix failing files, using your own Claude plan, capped at $2 per file.
- `--check-only` sets up and self-tests without touching Finder, launchd or Claude (for CI).
- `./uninstall.sh` removes everything the installer added to your Mac.

Re-run `install.sh` after updating.

## Three ways in

| How | When | What happens |
|---|---|---|
| **Finder:** right-click → Quick Actions → **Check Lottie** | One or more files, on demand | Notification with the outcome. The report opens (a summary page for several files). |
| **Inbox:** drop files into `~/Lotties/inbox` | Hands-off | Checked automatically, then moved to `passed/` or `needs-work/`. Claude tries a fix for each needs-work file into `fixed/`. |
| **Terminal:** `~/lottie-check/lottie-check FILE…` | Scripting, CI | Same checks. `--json` for machine output; exit 1 if any file fails. |

## What each file goes through

| Step | Cost | What runs | Mirrors Swish |
|---|---|---|---|
| Cache | ~0 s | Results keyed by file contents (`out/<name>-<hash>/result.json`) | An unchanged file is never re-tested (`--force` to override) |
| Lint | <0.1 s | Python | Hollow layers, zips Android can't open (Figma's own `.lottie` export), images missing from the zip, broken asset refs. Budgets: >250 vector paths, >16 mattes/masks drawn at once, or >24 MB of decoded images (AE banners: ~35 paths, ~2 mattes, ~8 MB) |
| iOS | ~1 s | `ios-harness/` on this Mac, lottie-ios **4.5.0**, Core Animation engine, Metal `CARenderer` | lottie-react-native 7.3.5 with a cached `file://`: `.lottie` → `LottieAnimationView(dotLottieUrl:)`, `.json` → `JSONDecoder` |
| Android | ~1 s/file, ~3 s per batch | lottie-android **6.5.2** under Robolectric (real parser, real Skia, no emulator), plus a draw-cost bench | The same parser `setAnimationFromUrl` ends in (`fromZipStreamSync` / `fromJsonInputStreamSync`) |

A typical new file takes 2–5 s and uses no tokens. Claude only runs on inbox files that fail or are over budget, capped at $2 each (`LOTTIE_FIX_BUDGET_USD`).

`--emulator` swaps Robolectric for the `lottie_check` emulator app. It loads the file over http like production and leaves it looping on screen. It's slower (about a minute to boot, ~2 GB of memory). Use it to watch a file play.

## Reading the draw cost

`draw cost per frame` is lottie-android's per-frame work: every frame is recorded into a display list, which is what the UI thread does on a phone, without GPU time. It runs on the M4, so only compare it with a known-good file. AE baseline `GourmetHMnoSKU.lottie`: p50 ≈ 0.03–0.1 ms. Don't judge smoothness by watching the emulator or by `dumpsys gfxinfo`: janky-frame % swung 0–37% between identical runs.

## Inbox

- Watched by the launchd agent `in.justswish.lottie-inbox` (template in `macos/`, installed in `~/Library/LaunchAgents`). Log: `~/Lotties/inbox.log`.
- Turn autofix on or off: re-run `./install.sh --with-inbox` with or without `--autofix`.
- Stop the watcher: `./uninstall.sh`, or `launchctl bootout gui/$(id -u)/in.justswish.lottie-inbox`.
- Fix know-how lives in the `lottie-fix` skill (`~/.claude/skills/lottie-fix/SKILL.md`). It also works in a normal Claude session ("fix this lottie").

## Fix tools (`fixes/`)

- `rezip_lottie.py in.lottie out.lottie`: rewrite a Figma `.lottie` zip that lottie-android can't open. The contents are unchanged.
- `pack_lottie.py in.json out.lottie`: pack a Figma JSON export. dotlottie-js 1.8.0 hollows Figma precomps, and lint flags that.
- `flatten_led_example.py`: flattens dot-matrix LED text into per-letter image layers using `bin/Rasterize` (`ios-harness/.build/release/Rasterize` in a source checkout).

## Keeping it in sync with Swish

When Swish bumps Lottie, update `ios-harness/Package.swift` (`exact:`) and `android/app/build.gradle.kts`, then bump `TOOL_VERSION` in `lottie-check` so cached results are redone. lottie-ios comes from Swish's `ios/Podfile.lock`. For lottie-android, the version that wins is the higher of the app's pin in `android/app/build.gradle` and lottie-react-native's own `android/build.gradle`.

## Setup notes (this Mac)

- Android SDK: Homebrew `android-commandlinetools`, JDK `openjdk@17`. Override with `ANDROID_SDK_ROOT` / `JAVA_HOME`.
- Java can't download the Gradle distribution here, so the wrapper zip was placed in `~/.gradle/wrapper/dists/gradle-8.14.3-bin/*/` with curl. Repeat that if the Gradle cache is ever wiped.
- The first Robolectric run downloads Android's runtime jar (~1 minute, once): to `~/.m2` from source, to `~/.lottie-check` from the bundle. Robolectric can't load it from a path with spaces.
