# lottie-check

Test `.lottie` / Lottie `.json` files against the players the Swish app ships, before uploading them.

## Install (once per Mac, ~5 minutes)

Needs macOS, [Homebrew](https://brew.sh) and Xcode Command Line Tools (`xcode-select --install`). Put this folder wherever you like (e.g. `~/lottie-check`), then:

```bash
./install.sh
```

The installer:

1. Adds Java 17 and the Android SDK via Homebrew. You may be asked to accept Google's SDK licence.
2. Builds both checkers.
3. Self-tests on `samples/`.
4. Adds the Finder Quick Action. Finder restarts once.

Options:

- `./install.sh --with-inbox` also watches `~/Lotties/inbox`.
- `./install.sh --with-inbox --autofix` also lets [Claude Code](https://claude.com/claude-code) try to fix failing files, using your own Claude plan, capped at $2 per file.
- `./uninstall.sh` removes everything the installer added to your Mac.

Re-run `./install.sh` after pulling updates.

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
| Lint | <0.1 s | Python | Hollow layers, images missing from the zip, broken asset refs. Budgets: >250 vector paths or >24 MB of decoded images (AE banners: ~35 paths, ~8 MB) |
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

- `pack_lottie.py in.json out.lottie`: pack a Figma JSON export. dotlottie-js 1.8.0 hollows Figma precomps, and lint flags that.
- `flatten_led_example.py`: flattens dot-matrix LED text into per-letter image layers using `ios-harness/.build/release/Rasterize`.

## Keeping it in sync with Swish

When Swish bumps Lottie, update `ios-harness/Package.swift` (`exact:`) and `android/app/build.gradle.kts`, then bump `TOOL_VERSION` in `lottie-check` so cached results are redone. lottie-ios comes from Swish's `ios/Podfile.lock`. For lottie-android, the version that wins is the higher of the app's pin in `android/app/build.gradle` and lottie-react-native's own `android/build.gradle`.

## Setup notes (this Mac)

- Android SDK: Homebrew `android-commandlinetools`, JDK `openjdk@17`. Override with `ANDROID_SDK_ROOT` / `JAVA_HOME`.
- Java can't download the Gradle distribution here, so the wrapper zip was placed in `~/.gradle/wrapper/dists/gradle-8.14.3-bin/*/` with curl. Repeat that if the Gradle cache is ever wiped.
- The first Robolectric run downloads Android's runtime jar (~1 minute, once).
