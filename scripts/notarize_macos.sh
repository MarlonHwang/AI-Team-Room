#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?version is required}"
DIST_ROOT="${2:-dist/macos}"
APP_PATH="$DIST_ROOT/AI-Team-Room.app"
ARCH="$(uname -m)"

if [[ "$ARCH" == "arm64" ]]; then
  RELEASE_ARCH="arm64"
else
  RELEASE_ARCH="x64"
fi

DMG_PATH="$DIST_ROOT/AI-Team-Room-$VERSION-macOS-$RELEASE_ARCH.dmg"
ZIP_PATH="$DIST_ROOT/AI-Team-Room-$VERSION-macOS-$RELEASE_ARCH.zip"
NOTARY_LOG="$DIST_ROOT/notarization-$RELEASE_ARCH.json"
NOTARY_INFO="$DIST_ROOT/notarization-info-$RELEASE_ARCH.json"

: "${APPLE_ID:?APPLE_ID is required}"
: "${APPLE_TEAM_ID:?APPLE_TEAM_ID is required}"
: "${APPLE_APP_SPECIFIC_PASSWORD:?APPLE_APP_SPECIFIC_PASSWORD is required}"

credentials=(
  --apple-id "$APPLE_ID"
  --team-id "$APPLE_TEAM_ID"
  --password "$APPLE_APP_SPECIFIC_PASSWORD"
)

retry() {
  local attempts="$1"
  shift
  local attempt=1
  until "$@"; do
    if (( attempt >= attempts )); then
      return 1
    fi
    echo "Attempt $attempt failed; retrying in 20 seconds..." >&2
    sleep 20
    attempt=$((attempt + 1))
  done
}

submit_json="$(mktemp)"
trap 'rm -f "$submit_json"' EXIT

# Submitting the DMG also creates a ticket for its nested app bundle. This lets
# us staple the app and build the final distributable ZIP without a second
# notarization submission.
retry 5 xcrun notarytool submit "$DMG_PATH" \
  "${credentials[@]}" \
  --no-s3-acceleration \
  --output-format json \
  > "$submit_json"

submission_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["id"])' "$submit_json")"
echo "Apple notarization submission: $submission_id"

accepted=false
for attempt in $(seq 1 180); do
  if xcrun notarytool info "$submission_id" "${credentials[@]}" \
      --output-format json > "$NOTARY_INFO"; then
    status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["status"])' "$NOTARY_INFO")"
    echo "Notarization status ($attempt/180): $status"
    case "$status" in
      Accepted)
        accepted=true
        break
        ;;
      Invalid|Rejected)
        retry 5 xcrun notarytool log "$submission_id" "${credentials[@]}" "$NOTARY_LOG" || true
        cat "$NOTARY_LOG" 2>/dev/null || true
        exit 1
        ;;
    esac
  else
    echo "Could not query notarization status; retrying." >&2
  fi
  sleep 20
done

if [[ "$accepted" != true ]]; then
  echo "Notarization did not finish within 60 minutes." >&2
  exit 1
fi

# Apple recommends inspecting the log even for an accepted submission.
retry 5 xcrun notarytool log "$submission_id" "${credentials[@]}" "$NOTARY_LOG"

retry 5 xcrun stapler staple "$APP_PATH"
retry 5 xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$APP_PATH"
xcrun stapler validate "$DMG_PATH"

# A ZIP cannot itself be stapled. Rebuild it after stapling the nested app.
rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

