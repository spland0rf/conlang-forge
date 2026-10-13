#!/usr/bin/env bash
# Creates the runnable Expo project in mobile/app from the committed sources (App.tsx + src/).
# Using the official generator keeps every package version matched to the current Expo Go app on your phone.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d app ]; then
  npx --yes create-expo-app@latest app --template blank-typescript --no-install
  (cd app && npm install && npx expo install expo-secure-store expo-status-bar)
fi
# Name, scheme and the app id (com.splandorf.conlang for both iOS and Android) come from app-identity.json.
node -e '
const fs=require("fs"); const f="app/app.json"; const j=JSON.parse(fs.readFileSync(f,"utf8")); const id=JSON.parse(fs.readFileSync("app-identity.json","utf8"));
const e=j.expo||j; Object.assign(e,{name:id.name,slug:id.slug,scheme:id.scheme}); e.ios=Object.assign(e.ios||{},id.ios); e.android=Object.assign(e.android||{},id.android);
fs.writeFileSync(f,JSON.stringify(j.expo?j:{expo:e},null,2));'
rm -rf app/src && cp -r src app/src && cp App.tsx app/App.tsx
echo "Sources copied. Start it with:  cd mobile/app && npx expo start"
