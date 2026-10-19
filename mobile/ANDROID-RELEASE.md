# Releasing the Android app (Google Play)

App id `com.splandorf.conlang`. Builds are made by Expo's cloud service (EAS), so you do not need Android Studio.

## One-time setup (on your laptop)

```bash
cd mobile && ./setup.sh                 # refreshes mobile/app with sources, icons, app.json, eas.json
cd app
npx eas-cli login                       # your free expo.dev account
npx eas-cli init                        # links the project; adds owner + projectId to app/app.json
```

Every command below is run from `mobile/app` and uses `npx eas-cli`, which downloads EAS on first use, so nothing needs
installing globally. (If you prefer a plain `eas` command, `npm install -g eas-cli` works, but then a shell that cannot
find `eas` — "eas: command not found" — means npm's global bin folder is not on your PATH; `npx eas-cli` avoids that.)

## 1. Test build you can install (APK)

```bash
npx eas-cli build -p android --profile preview
```
EAS prints a link/QR when it finishes. Open it on your phone and install the APK. Check: sign-in, Google sign-in
(returns to the app through `conlangforge://auth`), translate, create a language, download, delete account (use a
throwaway account).

## 2. Store build (AAB)

```bash
npx eas-cli build -p android --profile production
```
The first time, let EAS generate and keep the upload keystore. Download the `.aab` from the build page.
`autoIncrement` raises the version code every build; to change the visible version edit `version` in `mobile/app.json`.

## 3. Play Console

1. **Create app / use the existing profile** for `com.splandorf.conlang`. Turn on **Play App Signing** when asked.
2. **Testing > Internal testing**: create a release, upload the `.aab`, add yourself as a tester, install from the opt-in link. No review wait.
3. **Main store listing** (text below), icon `store/play-icon-512.png`, feature graphic `store/feature-graphic-1024x500.png`, at least 2 phone screenshots (take them from the preview build).
4. **App content** forms:
   - Privacy policy URL: `https://www.splandorf.com/conlang/static/privacy.html`
   - **Account deletion**: in-app path "Languages tab > Delete account"; web URL `https://www.splandorf.com/conlang/static/delete-account.html`
   - App access: "All or some functionality is restricted". Give a test account (email + password) that is already confirmed.
   - Ads: none. Target audience: 13+ (not children). Content rating questionnaire: no violence/sexual/etc. content; user-generated content: none shared between users.
   - **Data safety** (see below).
5. **Closed testing (personal accounts):** Google requires at least 12 testers opted in continuously for 14 days before you can apply for production access. Create a closed-testing track, upload the same AAB, add 12+ testers (a Google Group or an email list), have them opt in and install, and wait 14 days. Then apply for production in the Dashboard.
6. **Production**: create the release from the tested AAB and submit for review (typically a few days for a new app).

## Later releases

Bump nothing by hand, run `npx eas-cli build -p android --profile production`, upload the new AAB to the track.
To skip the manual upload, create a Play service-account JSON key (Play Console > Setup > API access), keep it on your laptop
only (never commit it, never paste it into a chat), then `npx eas-cli submit -p android --profile production --path <aab>`.

## Data safety answers

| Question | Answer |
|---|---|
| Collects data? | Yes |
| Personal info | Email address, name (display name): collected, not shared, required for the account, purpose: account management and app functionality |
| User content | Other user-generated content (languages, text to translate): collected; **shared with a third party** (Anthropic, for processing: service provider) |
| Photos | Only a picture the person chooses to show a writing style (shrunk on the phone, sent once for a style suggestion, never stored): collected, **shared with a third party** (Anthropic, service provider), optional. The app uses the system photo picker and requests no storage permission. |
| App activity | App interactions / usage counts: collected, not shared, purpose: app functionality (usage limits) |
| Encrypted in transit | Yes |
| Users can request deletion | Yes (in-app and web link above) |
| Data sold | No |

## Store listing text

**App name:** Conlang Forge
**Short description (80):** Invent languages for your fantasy world, and translate to and from them.
**Full description:**
Conlang Forge builds a complete constructed language for your story, game or world in seconds.

- Forge a language from a few settings, a sample of text you like, or just a press of a button.
- Read its grammar book and browse its two-way dictionary.
- Translate English into your language and back, with word-by-word glosses.
- Fine-tune sounds, word order, and grammar, and keep as many languages as you like.
- Design writing systems for your languages, write translations in them, and save them as images.
- Keep checkpoints of a language or script so you can look back or start a new version.
- Share the dictionary and grammar book as documents.

Your languages are saved to your account and work the same on the website.
Translation and sample analysis use an AI model; text you submit for those is sent to the model provider for processing.

## App icon

White glyph on purple (#6A3FC8), drawn by `scripts/make_icons.py` (rerun it to change colours or proportions). It writes the Expo assets (`assets/icon.png`, `adaptive-icon.png`, `splash-icon.png`), the Play icon, the website icons, and bare-native sets in `store/icons/` (`android-*`/`android-round-*` for mdpi to xxxhdpi, `ios-*` for every AppIcon size). The adaptive foreground keeps the glyph inside the central 66% so circular masks do not clip it.
