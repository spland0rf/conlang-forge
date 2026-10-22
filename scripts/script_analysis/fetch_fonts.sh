#!/bin/sh
# Fonts used only to measure scripts that Unicode does not encode. Not committed (see .gitignore); Alcarin Tengwar and Noto Sans Cuneiform are SIL OFL 1.1.
set -e
cd "$(dirname "$0")"
mkdir -p .fonts
tmp=$(mktemp -d)
git clone -q --depth 1 https://github.com/Tosche/Alcarin-Tengwar.git "$tmp/at"
cp "$tmp/at/Fonts Static/AlcarinTengwar-Regular.ttf" .fonts/
cp "$tmp/at/OFL.txt" .fonts/AlcarinTengwar-OFL.txt
git clone -q --depth 1 https://github.com/notofonts/cuneiform.git "$tmp/cu"
python3 build_cuneiform_font.py "$tmp/cu/sources/NotoSansCuneiform-Regular.ufo/glyphs" .fonts/NotoSansCuneiform-Regular.ttf
cp "$tmp/cu/OFL.txt" .fonts/NotoSansCuneiform-OFL.txt
rm -rf "$tmp"
