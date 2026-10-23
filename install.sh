#!/bin/zsh
# Install lottie-check for this Mac user.
#
#   ./install.sh                 command-line tool + Finder Quick Action "Check Lottie"
#   ./install.sh --with-inbox    also watch ~/Lotties/inbox (checks every file dropped in)
#   ./install.sh --with-inbox --autofix
#                                and let Claude Code try to fix files that fail (needs `claude`, uses your plan)
#
# Safe to re-run: it updates in place. Undo with ./uninstall.sh.
set -euo pipefail

DIR=${0:A:h}
WITH_INBOX=0
AUTOFIX=0
for arg in "$@"; do
  case $arg in
    --with-inbox) WITH_INBOX=1 ;;
    --autofix) AUTOFIX=1 ;;
    *) echo "unknown option: $arg"; exit 2 ;;
  esac
done

step() { print -P "\n%B==> $1%b" }
fail() { print -P "%F{red}✗ $1%f"; exit 1 }

step "Checking prerequisites"
[[ $(uname) == Darwin ]] || fail "macOS only"
xcode-select -p >/dev/null 2>&1 || fail "Xcode Command Line Tools missing: run  xcode-select --install  then re-run this script"
command -v brew >/dev/null || fail "Homebrew missing: install it from https://brew.sh then re-run this script"
BREW=$(brew --prefix)
# downloaded zips carry the quarantine flag; Finder refuses to run quarantined Quick Actions
xattr -dr com.apple.quarantine "$DIR" 2>/dev/null || true

step "Java 17 and Android SDK (Homebrew)"
for pkg in openjdk@17 android-commandlinetools; do
  if brew list "$pkg" >/dev/null 2>&1; then echo "$pkg already installed"; else brew install "$pkg"; fi
done
export JAVA_HOME="$BREW/opt/openjdk@17"
SDK="$BREW/share/android-commandlinetools"
SDKMANAGER="$SDK/cmdline-tools/latest/bin/sdkmanager"
if [[ ! -d "$SDK/platforms/android-35" || ! -d "$SDK/build-tools/35.0.0" ]]; then
  echo "Installing Android platform 35 + build tools. You may be asked to accept Google's SDK licence."
  "$SDKMANAGER" "platforms;android-35" "build-tools;35.0.0"
fi
echo "sdk.dir=$SDK" > "$DIR/android/local.properties"

step "Building the iOS checker (lottie-ios 4.5.0)"
(cd "$DIR/ios-harness" && swift build -c release -q)

step "Building the Android checker (lottie-android 6.5.2 under Robolectric)"
(cd "$DIR/android" && ./gradlew :app:compileDebugUnitTestKotlin -q)

step "Self-test on the bundled samples"
mkdir -p "$DIR/out"
set +e
"$DIR/lottie-check" "$DIR/samples/good.lottie" "$DIR/samples/broken.lottie" --force --no-open --json > "$DIR/out/selftest.json" 2> "$DIR/out/selftest.log"
set -e
python3 - "$DIR/out/selftest.json" <<'PY' || { tail -20 "$DIR/out/selftest.log"; fail "self-test failed (log above)"; }
import json, sys
results = {r["name"]: r for r in json.load(open(sys.argv[1]))}
good, broken = results["good.lottie"], results["broken.lottie"]
assert good["status"] == "pass", f"good.lottie should pass: {good['status']}"
assert broken["status"] == "fail" and not broken["ios"]["ok"] and not broken["android"]["ok"], "broken.lottie should fail on both"
print("good.lottie passes, broken.lottie fails on iOS and Android: checks work")
PY

step "Finder Quick Action: Check Lottie"
SERVICE="$HOME/Library/Services/Check Lottie.workflow"
rm -rf "$SERVICE"
mkdir -p "$HOME/Library/Services"
cp -R "$DIR/macos/Check Lottie.workflow" "$SERVICE"
sed -i '' "s#__LOTTIE_CHECK_DIR__#$DIR#g" "$SERVICE/Contents/document.wflow"
# Automator normally records this when a workflow is saved; without it the action stays out of the right-click menu
defaults write pbs NSServicesStatus -dict-add '"(null) - Check Lottie - runWorkflowAsService"' \
  '{ "presentation_modes" = { ContextMenu = 1; FinderPreview = 1; ServicesMenu = 1; TouchBar = 1; }; }'
/System/Library/CoreServices/pbs -flush >/dev/null 2>&1 || true
/System/Library/CoreServices/pbs -update >/dev/null 2>&1 || true
killall Finder 2>/dev/null || true
echo "Right-click .lottie/.json files → Quick Actions → Check Lottie"

if command -v claude >/dev/null; then
  step "Claude Code skill: lottie-fix"
  mkdir -p "$HOME/.claude/skills/lottie-fix"
  sed "s#~/lottie-check#$DIR#g" "$DIR/claude-skill/lottie-fix/SKILL.md" > "$HOME/.claude/skills/lottie-fix/SKILL.md"
  echo "In Claude Code: \"fix this lottie: <path>\""
fi

AGENT="$HOME/Library/LaunchAgents/in.justswish.lottie-inbox.plist"
if (( WITH_INBOX )); then
  step "Inbox watcher: ~/Lotties/inbox"
  if (( AUTOFIX )) && ! command -v claude >/dev/null; then
    fail "--autofix needs Claude Code (https://claude.com/claude-code); install it or drop --autofix"
  fi
  mkdir -p "$HOME/Lotties"/{inbox,passed,needs-work,fixed} "$HOME/Library/LaunchAgents"
  launchctl bootout "gui/$(id -u)/in.justswish.lottie-inbox" 2>/dev/null || true
  CLAUDE_DIR=$( (command -v claude >/dev/null && dirname "$(command -v claude)") || echo /usr/bin)
  sed -e "s#__LOTTIE_CHECK_DIR__#$DIR#g" -e "s#__HOME__#$HOME#g" -e "s#__AUTOFIX__#$AUTOFIX#g" \
      -e "s#__PATH__#$CLAUDE_DIR:$BREW/bin:/usr/bin:/bin:/usr/sbin:/sbin#g" \
      "$DIR/macos/in.justswish.lottie-inbox.plist" > "$AGENT"
  launchctl bootstrap "gui/$(id -u)" "$AGENT"
  echo "Drop files into ~/Lotties/inbox → sorted into passed/ or needs-work/$( (( AUTOFIX )) && echo ', fixes in fixed/ (max \$2 each)')"
fi

step "Done"
echo "Terminal:  $DIR/lottie-check FILE…   (see README.md)"
