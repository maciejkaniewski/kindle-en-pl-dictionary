#!/usr/bin/env python3
"""Check simulated Kindle lookups against expectations.

Uses `kindling-cli lookup`, which predicts what a Paperwhite opens for a tapped
(or selected) string.  The simulator reports a text position, so a test
"gave -> give" passes when "gave" opens the same position as "give".

Test file format (TSV, '#' comments):
    query<TAB>expected headword      e.g.  gave up<TAB>give up
    query<TAB>-                      the query must NOT resolve
    query<TAB>!other                 the query must resolve, but NOT to "other"
                                     (collisions: "saw" must open saw, not see)
    query<TAB>~text                  (needs --src) the entry the query opens
                                     contains "text", e.g. Polish<TAB>~polski

With --src (the OPF/XHTML build directory), "given -> give" also passes when
"given" opens its own entry that starts with the cross-reference "→ give"
(used when the inflected form is a word of its own, e.g. the adjective "given").
"""
import argparse
import glob
import html
import os
import re
import subprocess
import sys

POS_RE = re.compile(r"at text position (\d+)")


def lookup(kindling, mobi, word):
    res = subprocess.run([kindling, "lookup", mobi, word], capture_output=True, text=True)
    m = POS_RE.search(res.stdout + res.stderr)
    return int(m.group(1)) if res.returncode == 0 and m else None


def load_src(src):
    """headword (lower case) -> (headword, entry html) from the build sources."""
    entries = {}
    for path in sorted(glob.glob(os.path.join(src, "content*.html"))):
        text = open(path, encoding="utf-8").read()
        for e in re.findall(r"<idx:entry.*?</idx:entry>", text, re.S):
            hw = html.unescape(re.search(r'<idx:orth value="([^"]*)"', e).group(1))
            entries[hw.lower()] = (hw, e)
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mobi")
    ap.add_argument("tests")
    ap.add_argument("--kindling", default="kindling-cli")
    ap.add_argument("--src", help="build source dir, enables cross-reference checks")
    args = ap.parse_args()
    src = load_src(args.src) if args.src else {}

    cache = {}

    def pos(w):
        if w not in cache:
            cache[w] = lookup(args.kindling, args.mobi, w)
        return cache[w]

    failures = total = 0
    for line in open(args.tests, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        query, expected = (x.strip() for x in line.split("\t"))
        total += 1
        got = pos(query)
        if expected == "-":
            ok = got is None
            detail = "does not resolve" if ok else f"unexpectedly resolves (position {got})"
        elif expected.startswith("~"):
            text = expected[1:]
            hit = src.get(query.lower())
            ok = bool(hit) and got is not None and got == pos(hit[0]) and text in hit[1]
            detail = f"entry contains {text!r}" if ok else f"entry for {query!r} lacks {text!r} (or query does not open it)"
        elif expected.startswith("!"):
            other = pos(expected[1:])
            ok = got is not None and other is not None and got != other
            detail = (f"resolves to its own entry, not {expected[1:]}" if ok
                      else f"position {got}, must differ from {expected[1:]} at {other}")
        else:
            want = pos(expected)
            ok = got is not None and got == want
            detail = f"-> {expected}"
            if not ok and got is not None and query.lower() in src:
                own_hw, entry = src[query.lower()]
                xref = f"→ <b>{html.escape(expected, quote=True)}</b>"
                if xref in entry and got == pos(own_hw):
                    ok, detail = True, f"-> own entry '{own_hw}' with → {expected}"
            if not ok:
                detail = f"position {got}, expected {expected} at {want}"
        print(f"{'PASS' if ok else 'FAIL'}  {query!r:24} {detail}")
        failures += not ok
    print(f"\n{total - failures}/{total} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
