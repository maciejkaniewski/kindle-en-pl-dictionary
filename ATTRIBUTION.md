# Attribution and licenses

## What is licensed how

| Files | License |
|---|---|
| Dictionary content: the released `.mobi`, the generated OPF/XHTML, [`corrections/polish.tsv`](corrections/polish.tsv) and the preview images in [`docs/images/`](docs/images/) | [CC BY-SA 4.0](LICENSE-DATA) |
| Everything else, including `tools/`, `tests/`, the `Makefile` and the CI workflow | [MIT](LICENSE) |

The dictionary content is an adaptation of Wiktionary and is shared under the
same license. You may share and adapt it, including commercially, as long as
you give attribution and release your adaptation under the same license. Do not
distribute it with DRM or other technical restrictions (CC BY-SA §2(a)(5)(C)).

## Sources

| Source | What is used | Authors | License | Version |
|---|---|---|---|---|
| [Polish Wiktionary (Wikisłownik)](https://pl.wiktionary.org/) | English headwords with Polish meanings, labels, example sentences with Polish translations, phrasal verbs and idioms | Wikisłownik contributors | CC BY-SA 4.0 | [kaikki.org Polish extract](https://kaikki.org/dictionary/downloads/pl/), published 2026-10-30 |
| [English Wiktionary](https://en.wiktionary.org/) | English inflected forms, pronunciation, Polish translation tables, number of translations (used to rank phrasal verbs and idioms) | Wiktionary contributors | CC BY-SA 4.0 | [kaikki.org raw Wiktextract dump](https://kaikki.org/dictionary/rawdata.html), published 2026-10-30 |

Every entry corresponds to the Wiktionary pages with the same title, for
example <https://pl.wiktionary.org/wiki/give> and
<https://en.wiktionary.org/wiki/give>. The history of each page lists all of
its authors.

The Wiktionary data was extracted with Wiktextract:

> Tatu Ylonen. 2022. *Wiktextract: Wiktionary as Machine-Readable Structured
> Data.* In Proceedings of the 13th Language Resources and Evaluation
> Conference (LREC 2022), pages 1317–1325, Marseille, France.

## Changes made

Entries from both Wiktionaries are selected, merged, de-duplicated and
reformatted. English inflected forms are attached for lookup, inflected forms
of multi-word verbs are generated from their head verb (*give up* to *gave
up*), short cross-references are added (*saw* to *see*), the most common
phrasal verbs and idioms are listed under their base word, and errors in Polish
example sentences are corrected (see [`corrections/polish.tsv`](corrections/polish.tsv)).

## Acknowledgements

- The **Wikisłownik and Wiktionary communities**, who wrote all of the
  dictionary content.
- **[kaikki.org](https://kaikki.org/) and [Wiktextract](https://github.com/tatuylonen/wiktextract)**
  by Tatu Ylonen, for the machine-readable Wiktionary data.
- **[kindling](https://github.com/ciscoriordan/kindling)** by Francisco
  Riordan (MIT license), which compiles the `.mobi` and simulates Kindle
  lookups for the tests. It is downloaded at build time and not distributed
  with this project.

## Trademarks

Kindle is a trademark of Amazon.com, Inc. Wiktionary and Wikisłownik are
trademarks of the Wikimedia Foundation. Oxford Dictionary of English is a
trademark of Oxford University Press. This project is not affiliated with or
endorsed by any of them, and the names are used only to describe compatibility
and sources.
