#!/usr/bin/env python3
"""Manage corrections of Polish text taken from Wiktionary.

corrections/polish.tsv has one row per correction:

    headword  original  corrected  status  source  note

* original  - the Polish text exactly as it appears in the source data (an
              example translation or a definition)
* corrected - the replacement; "-" removes the example altogether
* status    - pending | approved | rejected   (the build applies only approved)
* source    - ai | human

Review workflow: AI-suggested rows are added as "pending"; a human changes the
status to "approved" or "rejected".  If Wiktionary itself fixes the original
text, the row stops matching and the build reports it as stale.

Commands:
  export  write a batch of example sentences to review, most frequent words first
  add     append suggestions (TSV: headword, original, corrected, note) as pending
  stats   count rows by status
"""
import argparse
import json
import os
import sys

DEFAULT = os.path.join(os.path.dirname(__file__), "..", "corrections", "polish.tsv")
FIELDS = ["headword", "original", "corrected", "status", "source", "note"]


def read_rows(path):
    """Plain tab-separated rows (fields never contain tabs or newlines)."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            line = line.rstrip("\n")
            if line:
                values = line.split("\t")
                rows.append(dict(zip(header, values + [""] * (len(header) - len(values)))))
    return rows


def write_rows(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["headword"].lower(), r["headword"], r["original"]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\t".join(FIELDS) + "\n")
        for r in rows:
            f.write("\t".join(r.get(k, "").replace("\t", " ") for k in FIELDS) + "\n")


def load_approved(path):
    """(headword, original) -> corrected, for the build."""
    return {(r["headword"], r["original"]): r["corrected"]
            for r in read_rows(path) if r["status"] == "approved"}


def cmd_export(args):
    done = {(r["headword"], r["original"]) for r in read_rows(args.corrections)}
    order = {}
    if args.priority:
        with open(args.priority, encoding="utf-8") as f:
            for i, w in enumerate(x.strip().lower() for x in f if x.strip()):
                order.setdefault(w, i)
    rows = []
    for line in open(args.records, encoding="utf-8"):
        r = json.loads(line)
        for s in r["senses"]:
            for en, pl in s["examples"][:1]:  # only the example the dictionary shows
                if (r["hw"], pl) not in done:
                    rows.append((order.get(r["hw"].lower(), 10**9), r["hw"], s["gloss"], en, pl))
    rows.sort(key=lambda x: (x[0], x[1].lower()))
    batch = rows[args.start:args.start + args.count]
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("headword\tgloss\tenglish\tpolish\n")
        for _, hw, gloss, en, pl in batch:
            f.write(f"{hw}\t{gloss}\t{en}\t{pl}\n")
    print(f"exported {len(batch)} examples ({len(rows)} not yet reviewed) to {args.output}")


def cmd_add(args):
    rows = read_rows(args.corrections)
    have = {(r["headword"], r["original"]) for r in rows}
    added = 0
    with open(args.suggestions, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#") or line.startswith("headword\t"):
                continue
            hw, original, corrected, *note = line.split("\t")
            if (hw, original) in have or original == corrected:
                continue
            rows.append({"headword": hw, "original": original, "corrected": corrected,
                         "status": "pending", "source": args.source,
                         "note": note[0] if note else ""})
            have.add((hw, original))
            added += 1
    write_rows(args.corrections, rows)
    print(f"added {added} pending suggestions to {args.corrections}")


def cmd_stats(args):
    from collections import Counter
    c = Counter(r["status"] for r in read_rows(args.corrections))
    print(", ".join(f"{k}: {v}" for k, v in sorted(c.items())) or "no corrections yet")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corrections", default=os.path.normpath(DEFAULT))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("export", help="export a batch of examples to review")
    p.add_argument("--records", default="build/full/records.jsonl")
    p.add_argument("--priority", help="word list, most frequent first (optional)")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--count", type=int, default=200)
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("add", help="append suggestions as pending")
    p.add_argument("suggestions", help="TSV: headword, original, corrected[, note]")
    p.add_argument("--source", default="ai", choices=["ai", "human"])
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("stats", help="count corrections by status")
    p.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
