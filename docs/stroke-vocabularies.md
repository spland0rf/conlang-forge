# Stroke vocabularies from hand-drawn stroke charts

Source: the user's hand-drawn build-up charts (one row per letter: the sound, the letter, then the letter built up stroke by stroke, the new
stroke in red) for **Tamil** (3 pages), **Bengali** (3 pages) and **Devanagari** (3 pages), plus font-derived drafts for Hangul, Greek, Latin,
Cyrillic, Hebrew, Arabic and Thai (`scripts/script_analysis/stroke_charts/`). Elvish and Amharic (Ethiopic) charts are still to come.

Reading rules agreed with the user:
- Red is the new stroke; red drawn over black wins. Scratched-out patches, ink blobs and the small dots between stages are not part of any letter.
- Stroke order is not significant; it only has to be plausible: connected strokes in sequence, left to right and top to bottom as the tie-breaker.
- A stroke made only of vertical and horizontal segments is stored as **one stroke per segment**. A smooth curve stays **one stroke** (the Tamil bells,
  swoops, loops, the self-crossing curve of Bengali হ, the S-curve of Bengali জ). The double hump "3" is one stroke as drawn and may be stored as two single humps.
- Real dots (Bengali ড় ঢ় য় র, Devanagari ङ) are separate dot strokes drawn last. Circles and curls in Tamil are drawn loops, never dots.
- Where the chart and a standard glyph differ, the chart wins.

## Devanagari and Bengali: the headline family

Almost every consonant is a **top bar** (the headline, drawn first in consonants; last in the Devanagari vowels अ आ ओ औ) over a **T-stem**, with a **body** chosen
from a small set and sometimes one or two small extras. Bar-less letters: Devanagari थ ध भ ङ and the short extender of ध and भ (not a full bar); Bengali ঋ এ ঐ ঙ শ.

| Atom | Where it appears |
|---|---|
| top bar | all headline consonants |
| T-stem (full height, centre or right of centre) | ক ঘ ब ट ठ ड ढ ण त न प फ ... |
| short stem (very short drop from the bar) | ह ; Bengali ম/য starts |
| hook hanging a little right of the bar's centre | र ; Bengali র |
| triangle head (two slants meeting at a point, left of the stem) | ব ক ঘ ধ ब च |
| ring body hung on the stem | ঠ ড ভ ठ |
| double hump "3" on the left | अ आ ओ औ ; ঞ ক-forms |
| S-curve | জ ज ; ঞ |
| crossing diagonal | ফ ষ শ ফ श ष |
| two hooked arms | घ ধ |
| curled tick (top, above the bar, or bottom) | Bengali ই ঈ এ ঐ |
| small curl / long tail at the foot | ऋ ॠ ऌ ॡ द |
| dot below | Bengali ড় ঢ় য় র |

Devanagari pt. 1-3 letters: vowels अ आ इ ई उ ऊ ऋ ॠ ऌ ॡ ए ऐ ओ औ, consonants क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह.
Bengali pg. 1-3: অ আ ই ঈ উ ঊ ঋ এ ঐ ও ঔ ক খ গ ঘ ঙ চ ছ জ ঝ ঞ ট ঠ ড ড় ঢ ঢ় ণ ত থ দ ধ ন প ফ ব (ba and va are one letter) ভ ম য য় র ল শ ষ স হ.

## Tamil: the foot family

No headline. Letters hang on a vertical, a **foot bar**, a **shoulder**, or a chain of **loops**.

| Family | Letters | Atoms |
|---|---|---|
| vertical | அ ஆ எ ஏ | full vertical; bar off it at about three quarters down (`HJOIN`); crossed "+" bar (ஆ); bell swoop ending in an open curl |
| shoulder | ஈ ந ண ṅa ர ற | Γ/Π shoulder with optional inner arch; right vertical; hooked tail that curls down and left |
| foot bar | உ ஊ ட ப ம ய ழ | L (vertical + foot bar) with a right post (ப), an arch (ம), a left tick (ய), an inner loop and tail curl (ழ) |
| ring and swoop | ஐ ஒ ஓ ஔ | ring + bell swoop ending in an open (not closed) curl |
| loop with crossing | க ச | vertical with a loop at the foot, a short bar across, a small square corner hook (ச) |
| chained loops | ண ள ன ல | one to three small rings in a row, each with an arm, finished by a vertical from the last arm (ள tail is three touching atoms, left to right) |
| closed circle forms | ஜ ஶ்ரீ | S-curve ending in a closed circle (ஜ); base swoop starting in a closed oval and rising to a small ring-head curl (ஶ்ரீ) |
| dot triple | ஃ | three small circles in a triangle |
| conjuncts | க்ஷ ஶ்ரீ | க plus ஶ parts; a later layer on top of single letters |

Separate letters, not variants: dotted ṅa (ங with a dot over the n) and plain na (ந).

## Hangul (font-derived)

Straight bars, drops, boxes and rings: corners (ㄱ ㄴ), open boxes (ㄷ ㅌ ㄹ), boxes (ㅁ ㅂ), ladders (ㅍ), pairs of diagonals (ㅅ ㅈ ㅊ), rings with a bar and tick (ㅇ ㅎ),
stems with ticks (ㅏ ㅑ ㅓ ㅕ ㅣ) and bars with ticks (ㅗ ㅛ ㅜ ㅠ ㅡ). One stroke per straight segment.

## Thai (font-derived)

A **loop at the head** with a stem (ก ข ค), a cap over it (จ ฉ), an arch (น บ ป ม), an S (ส ซ), a loop turning back on the stem (ฆ ณ), two rings side by side (ธ ฒ); stems end bare,
in a foot bar, a hook left or right, or a tick.

## In the generator (pen v3)

`conlang_forge/script/pen_vocab.py` holds one recipe family per vocabulary above (`headline`, `foot`, `loop_head`, `jamo`), selected by the `pen_frame` dial; `pen.garnish`
adds attached ticks and crossing bars from the `stroke_ticks` and `stroke_crossings` dials. The presets use them: Devanagari and Bengali `headline`, Tamil `foot`, Thai `loop_head`,
Hangul `jamo`.
