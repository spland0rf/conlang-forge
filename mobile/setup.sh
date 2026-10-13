#!/usr/bin/env bash
# Creates the runnable Expo project in mobile/app from the committed sources (App.tsx + src/).
# Using the official generator keeps every package version matched to the current Expo Go app on your phone.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d app ]; then
  npx --yes create-expo-app@latest app --template blank-typescript --no-install
  (cd app && npm install)
fi
# Safe to repeat: adds any package a newer version of the app needs.
(cd app && npx expo install expo-secure-store expo-status-bar expo-web-browser expo-linking expo-crypto)
rm -rf app/src && cp -r src app/src && cp App.tsx app/App.tsx
echo "Sources copied. Start it with:  cd mobile/app && npx expo start"
