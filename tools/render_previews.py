#!/usr/bin/env python3
"""Render README preview images from the built dictionary.

Each preview shows a sentence with the selected word or phrase, and below it
the start of the dictionary entry the Kindle opens, roughly as the lookup
popup shows it.  The images are rendered with headless Chrome from the real
build output (build/full/src), so they stay in sync with the dictionary.

Requirements: Google Chrome or Chromium, ImageMagick (`convert`).

    python3 tools/render_previews.py --src build/full/src --out docs/images
"""
import argparse
import glob
import html
import os
import re
import shutil
import subprocess
import tempfile

# (file name, sentence, selected text, headword the Kindle opens)
CASES = [
    ("gave", "She gave me her old bike.", "gave", "give"),
    ("broke-the-ice", "His joke broke the ice.", "broke the ice", "break the ice"),
    ("saw", "I saw him yesterday.", "saw", "saw"),
    ("looking-forward-to", "I am looking forward to the holidays.", "looking forward to", "look forward to"),
    ("mice", "Two mice ran under the table.", "mice", "mouse"),
    ("went", "We went home early.", "went", "go"),
    ("may", "May I come in?", "May", "may"),
]
HERO = ["gave", "broke-the-ice", "saw"]

CSS = """
body { margin: 0; background: #ffffff; font-family: 'DejaVu Sans', sans-serif; }
.row { display: flex; gap: 26px; padding: 18px; align-items: flex-start; }
.case { width: 430px; }
.book { font: 21px/1.5 'DejaVu Serif', serif; color: #222; margin: 0 4px 12px; }
.sel { background: #e8e6df; border-bottom: 2px solid #222; padding: 0 2px; }
.card { background: #f6f5f0; border: 1.5px solid #333; border-radius: 10px; overflow: hidden; }
.entry { padding: 14px 18px 0; font-size: 15.5px; line-height: 1.45; color: #111;
         height: 255px; overflow: hidden; position: relative; }
.entry::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 42px;
                background: linear-gradient(rgba(246,245,240,0), #f6f5f0); }
.foot { border-top: 1px solid #c9c7bf; padding: 7px 18px 9px; font-size: 12.5px; color: #555; }
"""


def load_entries(src):
    entries = {}
    for path in sorted(glob.glob(os.path.join(src, "content*.html"))):
        for e in re.findall(r"<idx:entry.*?</idx:entry>", open(path, encoding="utf-8").read(), re.S):
            hw = html.unescape(re.search(r'<idx:orth value="([^"]*)"', e).group(1))
            body = re.sub(r"<idx:infl>.*?</idx:infl>", "", e)
            body = re.sub(r"</?idx:(orth|entry)[^>]*>", "", body)
            entries[hw] = body
    return entries


def case_html(sentence, selected, entry):
    i = sentence.find(selected)
    book = (html.escape(sentence[:i]) + f'<span class="sel">{html.escape(selected)}</span>'
            + html.escape(sentence[i + len(selected):]))
    return (f'<div class="case"><div class="book">{book}</div><div class="card">'
            f'<div class="entry">{entry}</div>'
            f'<div class="foot">Słownik angielsko-polski (Wiktionary)</div></div></div>')


def render(chrome, page, png, width, tmp):
    src = os.path.join(tmp, "page.html")
    with open(src, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset=utf-8><style>{CSS}</style>{page}")
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
                    f"--user-data-dir={os.path.join(tmp, 'profile')}", "--force-device-scale-factor=2",
                    f"--window-size={width},420", f"--screenshot={png}", f"file://{src}"],
                   check=True, capture_output=True, timeout=120)
    # trim the white margin, add a small border, keep the file small
    subprocess.run(["convert", png, "-trim", "-bordercolor", "white", "-border", "16",
                    "-colors", "64", "-strip", png], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="build/full/src")
    ap.add_argument("--out", default="docs/images")
    ap.add_argument("--chrome", default=shutil.which("google-chrome") or shutil.which("chromium") or "chromium")
    args = ap.parse_args()

    entries = load_entries(args.src)
    os.makedirs(args.out, exist_ok=True)
    by_name = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, sentence, selected, hw in CASES:
            block = case_html(sentence, selected, entries[hw])
            by_name[name] = block
            render(args.chrome, f'<div class="row">{block}</div>', os.path.join(args.out, f"{name}.png"), 500, tmp)
        hero = "".join(by_name[n] for n in HERO)
        render(args.chrome, f'<div class="row">{hero}</div>', os.path.join(args.out, "hero.png"), 1450, tmp)
    print(f"wrote {len(CASES) + 1} images to {args.out}")


if __name__ == "__main__":
    main()
