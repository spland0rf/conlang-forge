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
(cd app && npx expo install expo-secure-store expo-status-bar expo-web-browser expo-linking expo-crypto expo-file-system expo-sharing react-native-svg react-native-view-shot expo-image-picker expo-image-manipulator)
# Pure-JavaScript JPEG decoder: the picture is measured on the phone, as it is in the website.
(cd app && npm install jpeg-js)
rm -rf app/src app/assets && cp -r src app/src && cp -r assets app/assets && cp App.tsx app/App.tsx
# Store identity (name, package com.splandorf.conlang, icons, link scheme) and the EAS build profiles.
cp eas.json app/eas.json
# Keep what `eas init` added (owner, extra.eas.projectId) when app.json is refreshed.
node -e '
const fs=require("fs"),n=JSON.parse(fs.readFileSync("app.json")).expo;
let o={};try{o=JSON.parse(fs.readFileSync("app/app.json")).expo||{}}catch{}
if(o.owner)n.owner=o.owner; if(o.extra)n.extra=o.extra;
fs.writeFileSync("app/app.json",JSON.stringify({expo:n},null,2));'

echo "Sources, icons and app.json copied. Start it with:  cd mobile/app && npx expo start"
