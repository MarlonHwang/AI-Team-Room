#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"
VERSION="${1:-0.1.1}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_VENV="$REPO_ROOT/.venv-build-macos"
BUILD_PYTHON="$BUILD_VENV/bin/python"
WORK_ROOT="$REPO_ROOT/build/macos"
DIST_ROOT="$REPO_ROOT/dist/macos"
APP_PATH="$DIST_ROOT/AI-Team-Room.app"
ARCH="$(uname -m)"

if [[ "$ARCH" == "arm64" ]]; then
  RELEASE_ARCH="arm64"
else
  RELEASE_ARCH="x64"
fi

if [[ ! -x "$BUILD_PYTHON" ]]; then
  "$PYTHON" -m venv "$BUILD_VENV"
fi

"$BUILD_PYTHON" -m pip install --disable-pip-version-check \
  -r "$REPO_ROOT/requirements-build.txt"
"$BUILD_PYTHON" -m pip install --disable-pip-version-check --no-deps "$REPO_ROOT"

rm -rf "$WORK_ROOT" "$DIST_ROOT"
mkdir -p "$WORK_ROOT/spec" "$WORK_ROOT/work" "$DIST_ROOT"

COMMON=(
  --noconfirm
  --clean
  --paths "$REPO_ROOT/src"
  --collect-data ai_team_room
  --workpath "$WORK_ROOT/work"
  --specpath "$WORK_ROOT/spec"
  --distpath "$DIST_ROOT"
)

"$BUILD_PYTHON" -m PyInstaller "${COMMON[@]}" \
  --onedir \
  --windowed \
  --osx-bundle-identifier studio.madoro.aiteamroom \
  --name AI-Team-Room \
  "$REPO_ROOT/scripts/windows_server_entry.py"

"$BUILD_PYTHON" -m PyInstaller "${COMMON[@]}" \
  --onefile \
  --name aitr \
  "$REPO_ROOT/scripts/windows_client_entry.py"

cp "$DIST_ROOT/aitr" "$APP_PATH/Contents/MacOS/aitr"
chmod +x "$APP_PATH/Contents/MacOS/aitr"

set_plist_string() {
  local key="$1"
  local value="$2"
  local plist="$APP_PATH/Contents/Info.plist"
  if ! /usr/libexec/PlistBuddy -c "Set :$key $value" "$plist"; then
    /usr/libexec/PlistBuddy -c "Add :$key string $value" "$plist"
  fi
}

set_plist_string CFBundleDisplayName "AI Team Room"
set_plist_string CFBundleShortVersionString "$VERSION"
set_plist_string CFBundleVersion "$VERSION"

if [[ -n "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp \
    --sign "$APPLE_SIGNING_IDENTITY" "$APP_PATH"
else
  codesign --force --deep --sign - "$APP_PATH"
fi

ZIP_PATH="$DIST_ROOT/AI-Team-Room-$VERSION-macOS-$RELEASE_ARCH.zip"
DMG_PATH="$DIST_ROOT/AI-Team-Room-$VERSION-macOS-$RELEASE_ARCH.dmg"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
hdiutil create -quiet -volname "AI Team Room" -srcfolder "$APP_PATH" \
  -ov -format UDZO "$DMG_PATH"

echo "$ZIP_PATH"
echo "$DMG_PATH"
