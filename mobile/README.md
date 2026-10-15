# Conlang Forge mobile app (iOS and Android)

React Native + Expo (TypeScript). It talks to the same server and API as the website, so languages, accounts
and limits are shared.

## Run it on your phone

On a computer with Node 20+ installed:

```bash
cd mobile
./setup.sh                  # one time: creates mobile/app and installs packages
cd app && npx expo start    # prints a QR code
```

Install **Expo Go** from the App Store / Play Store, then scan the QR code (iPhone: Camera app; Android: inside Expo Go).
The phone and computer must be on the same Wi-Fi. If they cannot see each other, use `npx expo start --tunnel`.

After you change files in `mobile/src` or `mobile/App.tsx`, run `./setup.sh` again to copy them into `mobile/app`.

The app opens to the live site (`https://www.splandorf.com/conlang`). To test against another server, tap
"Server" at the bottom of the sign-in screen.

## What is in each stage

1. Sign in, create account ("Check your email" screen), forgot password, languages list, translate both ways. **(this stage)**
2. Dictionary and grammar book (read only).
3. Create a language, including from a sample with the length meter.
4. Settings editor.
5. Google sign-in and email links that open the app.
6. Writing systems: a Writing tab on each language, the writing area under a translation (with image and SVG download), a Writing systems list and editor (every dial, describe the look in words, or from a picture), and Versions (checkpoints) for languages and writing systems.

The picture feature uses `expo-image-picker`, `expo-image-manipulator` and the pure-JavaScript `jpeg-js` (measured on the phone by `src/measure.ts`, a port of the website's `imagemeasure.js`). `./setup.sh` installs them. Written text is drawn with `react-native-svg` and saved as an image with `react-native-view-shot`.

## Tests

The API client (tokens, refresh, errors) has plain Node tests:

```bash
npx tsx mobile/tests/api.test.ts
```

The other test files (`content`, `settings`, `create`, `google`, `scripts`, `measure`, `svg`) run the same way. `measure.test.ts` checks the phone's picture measuring against the website's, number for number. Type-check without installing React Native: `npx tsc -p mobile/tsconfig.check.json` (the `tests/*` Node typing lines it prints are expected).
