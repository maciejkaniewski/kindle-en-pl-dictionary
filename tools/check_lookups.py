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
"""
import argparse
import re
import subprocess
import sys

POS_RE = re.compile(r"at text position (\d+)")


def lookup(kindling, mobi, word):
    res = subprocess.run([kindling, "lookup", mobi, word], capture_output=True, text=True)
    m = POS_RE.search(res.stdout + res.stderr)
    return int(m.group(1)) if res.returncode == 0 and m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mobi")
    ap.add_argument("tests")
    ap.add_argument("--kindling", default="kindling-cli")
    args = ap.parse_args()

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
        elif expected.startswith("!"):
            other = pos(expected[1:])
            ok = got is not None and other is not None and got != other
            detail = (f"resolves to its own entry, not {expected[1:]}" if ok
                      else f"position {got}, must differ from {expected[1:]} at {other}")
        else:
            want = pos(expected)
            ok = got is not None and got == want
            detail = f"-> {expected}" if ok else f"position {got}, expected {expected} at {want}"
        print(f"{'PASS' if ok else 'FAIL'}  {query!r:24} {detail}")
        failures += not ok
    print(f"\n{total - failures}/{total} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
