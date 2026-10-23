#!/bin/zsh
# Remove what install.sh added to this Mac. Leaves this folder, ~/Lotties and Homebrew packages alone.
set -u

launchctl bootout "gui/$(id -u)/in.justswish.lottie-inbox" 2>/dev/null && echo "stopped inbox watcher"
rm -f "$HOME/Library/LaunchAgents/in.justswish.lottie-inbox.plist"
rm -rf "$HOME/Library/Services/Check Lottie.workflow" && echo "removed Quick Action"
# remove only our entry; the dict also holds the user's settings for every other service
python3 - <<'PY'
import plistlib, subprocess
key = "(null) - Check Lottie - runWorkflowAsService"
raw = subprocess.run(["defaults", "export", "pbs", "-"], capture_output=True).stdout
if raw:
    prefs = plistlib.loads(raw)
    if prefs.get("NSServicesStatus", {}).pop(key, None) is not None:
        subprocess.run(["defaults", "import", "pbs", "-"], input=plistlib.dumps(prefs))
PY
/System/Library/CoreServices/pbs -update >/dev/null 2>&1 || true
rm -rf "$HOME/.claude/skills/lottie-fix" && echo "removed lottie-fix skill"
echo "Done. Delete this folder to remove the tool itself."
