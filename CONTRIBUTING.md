# Contributing

Thanks for helping to improve the dictionary. The most useful contributions
are corrections of the Polish text and reports from Kindle models that have
not been tested yet.

## Reporting a problem

Open an [issue](../../issues) with the word you looked up, what the Kindle
showed (a photo helps) and what you expected. For device reports, include the
Kindle model and its firmware version (*Settings → Device Options → Device
Info*).

## Corrections of Polish text

The Polish meanings and example sentences come from Wiktionary and are
sometimes wrong. Corrections live in
[`corrections/polish.tsv`](corrections/polish.tsv), one tab-separated row per
change:

| Column | Meaning |
|---|---|
| `headword` | the English entry |
| `original` | the Polish text exactly as it appears in the source data |
| `corrected` | the replacement; `-` removes an example |
| `status` | `pending`, `approved` or `rejected`; the build applies only `approved` rows |
| `source` | `ai` or `human` |
| `note` | what was wrong |

Only real errors are corrected: wrong meanings, typos, grammar errors and
broken examples. A sentence that is correct but could be phrased differently
is left as it is. Suggestions made with the help of AI stay `pending` until a
person has reviewed them. If Wiktionary fixes a sentence itself, the build
reports the correction as stale.

`tools/corrections.py export` writes the next batch of examples to review,
most frequent words first; `tools/corrections.py stats` counts the rows by
status.

## Building from source

Requirements: Linux or macOS, Python 3.10+, `curl` and about 4 GB of disk
space.

```sh
tools/download.sh   # Wiktionary data from kaikki.org (~3.2 GB) and kindling
make test           # build the dictionary (~5 min) and run the lookup tests
make test-book      # build the test book for checking a real Kindle
```

The dictionary is written to `build/full/kindle-en-pl-dictionary.mobi`, the
test book to `build/device/dictionary-test.azw3`.

How the build works:

1. `tools/extract.py` reads the kaikki.org Wiktionary data: Polish meanings
   and examples from the Polish Wiktionary, English inflected forms and Polish
   translations from the English Wiktionary.
2. `tools/build.py` merges both sources per headword, generates the inflected
   forms of multi-word verbs (*give up* → *gave up*), resolves words that are
   also inflections of other words (*saw*), applies approved corrections and
   compiles the `.mobi` with [kindling](https://github.com/ciscoriordan/kindling).
3. `tools/check_lookups.py` uses kindling's lookup simulator to check that,
   for example, *gave up* opens *give up* (`tests/lookups.tsv`).

`tools/render_previews.py` renders the README images from the build output
(requires Google Chrome or Chromium and ImageMagick).

## Releases

GitHub Actions builds the dictionary and runs the tests on every push. Pushing
a tag such as `v0.1.0` publishes a release with the dictionary and the test
book attached.
