# Web and mobile: what matches and what differs

Both clients talk to the same backend (`/api/...`), so data, permissions and limits are identical. Screens are written twice
(vanilla JS in `conlang_forge/web/static/js`, React Native in `mobile/src`), so a change to a screen has to be made in both.
Options that come from a catalogue the server sends (writing-system dials, translator settings groups) appear in both
automatically. Keep this list current when either side changes. Last reviewed: 2026-10-20.

## Same on both
| Area | Notes |
|---|---|
| Sign-in | Email and password, Google sign-in, forgot password. Email verification links open in a browser on both. |
| Languages | Your list plus a Create a language area: forge (name, seed, optional settings) or start from a sample. Web: a panel beside the list. Mobile: a card above the list that opens each form as its own screen. |
| Language tabs | Overview, Translate, Writing, Settings, Versions, Dictionary, Grammar book, Downloads. |
| Writing systems | Your list plus a **Create a writing system** area where the look is chosen *before* it is created: surprise me, from a description, or from a picture, with a name, the language it is designed for, a seed, and optional Style settings (anything you fix wins over what the description or picture suggests). Creating it opens the editor. Editor with every dial (keep/release, Randomize, seed), designed-for language, make primary, delete, describe the look (words or a picture), sample text and sentences. |
| Versions | Checkpoints of languages and writing systems; read-only view; new version from an old one. |
| Admin (admins only) | Users (limits, plan, status), Usage charts, Log, Settings. |
| Look | White pages, pale lavender highlights, black text, purple header with white text and yellow emphasis (website and app). The app icon is the same glyph. |

## Different on purpose (the platform suggests it)
| Area | Web | Mobile |
|---|---|---|
| Navigation | Top bar: Languages, Writing systems, Admin (admins), Account | Tab bar: Languages, Writing systems, Admin (admins only) |
| Settings tab | Sections shown as cards | Sections fold open and closed (language settings: only "Sounds" starts open) |
| Writing-system editor | All dial groups open | Foldable groups; "Shape mix" and "Letters" start folded; a sticky sample stays in view while dials change |
| Saving a picture of written text | Download PNG / SVG buttons (browser download) | Share icon (share sheet) and Save PNG (system folder picker); Save SVG (folder picker). No Share SVG: messaging apps do not accept SVG |
| Picture for "describe the look" | File chooser; the browser shrinks and measures it (`imagemeasure.js`) | Photo library; shrunk with expo-image-manipulator, measured by `src/measure.ts` (a port with a test that it equals the website's output) |

## Missing on mobile (candidates for later)
- Account page: change or set password, model usage, delete account is a separate screen on mobile (`DeleteAccount.tsx`).
- Token meter in the header and the "confirm your email" banner.
- Email-verification and password-reset result pages (the links open the website).
- Charts: the admin Usage page has a table view and tap-to-inspect instead of hover tooltips.

## Missing on web
- Save to a chosen folder (the browser downloads to its own folder).
- Folding of the dial groups in the writing-system editor.

## How to keep them in step
1. A change to what the server returns or accepts: update the API tests, then both clients (the mobile API shapes live in `mobile/src/types.ts`).
2. A new dial or setting in a catalogue: nothing to do on either client unless it needs a new control type (then `scripts.js` and `mobile/src/screens/ScriptEditor.tsx`).
3. A change to a screen's layout or wording: make it in both, or add a row above under "Different on purpose" or "Missing".
4. Colours: web tokens in `style.css` (`--purple`, `--sunk`, `--saffron`...); mobile `mobile/src/ui/theme.ts`. Change both together.
5. Paths: the site is served under `/conlang/`, so web files use relative paths (a test checks this).
