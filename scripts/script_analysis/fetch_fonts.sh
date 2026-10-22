#!/bin/sh
# Fonts used only to measure scripts that Unicode does not encode. Not committed (see .gitignore); Alcarin Tengwar is SIL OFL 1.1.
set -e
cd "$(dirname "$0")"
mkdir -p .fonts
tmp=$(mktemp -d)
git clone -q --depth 1 https://github.com/Tosche/Alcarin-Tengwar.git "$tmp/at"
cp "$tmp/at/Fonts Static/AlcarinTengwar-Regular.ttf" .fonts/
cp "$tmp/at/OFL.txt" .fonts/AlcarinTengwar-OFL.txt
rm -rf "$tmp"
