#!/usr/bin/env bash
# build_dmg.sh — wrap dist/FihsihCalc.app into a distributable .dmg
#
# Prereqs:
#   brew install create-dmg
#
# Run from the project root after: pyinstaller build.spec
#
set -euo pipefail

APP_NAME="Carbon"
DIST_DIR="dist"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"
DMG_PATH="${DIST_DIR}/${APP_NAME}.dmg"

if [ ! -d "$APP_PATH" ]; then
  echo "error: ${APP_PATH} not found. Run 'pyinstaller build.spec' first." >&2
  exit 1
fi

if ! command -v create-dmg >/dev/null 2>&1; then
  echo "error: create-dmg not found. Install with: brew install create-dmg" >&2
  exit 1
fi

rm -f "$DMG_PATH"

create-dmg \
  --volname "${APP_NAME}" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 175 190 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 425 190 \
  "$DMG_PATH" \
  "$APP_PATH"

echo "Created ${DMG_PATH}"

# --- Optional: codesign + notarize (requires a paid Apple Developer account) ---
# Without this, first launch shows a Gatekeeper "unidentified developer" warning
# that users have to right-click > Open to bypass.
#
# codesign --deep --force --verify --verbose \
#   --sign "Developer ID Application: Your Name (TEAMID)" "$APP_PATH"
#
# xcrun notarytool submit "$DMG_PATH" \
#   --apple-id "you@example.com" \
#   --team-id "TEAMID" \
#   --password "app-specific-password" \
#   --wait
#
# xcrun stapler staple "$DMG_PATH"
