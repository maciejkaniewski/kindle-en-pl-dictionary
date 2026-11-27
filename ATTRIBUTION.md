# Attribution and data sources

The dictionary content produced by this project (the `.mobi` files and the
generated OPF/XHTML sources) is a derivative of Wiktionary and is licensed under
the **Creative Commons Attribution-ShareAlike 4.0 International** licence
([LICENSE-DATA](LICENSE-DATA), <https://creativecommons.org/licenses/by-sa/4.0/>).
You may share and adapt it, including commercially, as long as you give
attribution and release your adaptations under the same licence. Do not
distribute it with DRM or other technical restrictions (CC BY-SA §2(a)(5)(C)).

The build tools in this repository are licensed separately under the MIT
licence ([LICENSE](LICENSE)).

## Sources

| Source | What we use | Authors | Licence | Version used |
|---|---|---|---|---|
| [Polish Wiktionary (Wikisłownik)](https://pl.wiktionary.org/), via the [kaikki.org Polish extract](https://kaikki.org/dictionary/downloads/pl/) | English headwords with Polish definitions, register labels, example sentences with Polish translations, phrasal verbs | Wikisłownik contributors | CC BY-SA 4.0 | kaikki.org extract, published 2026-10-30 |
| [English Wiktionary](https://en.wiktionary.org/), via the [kaikki.org raw Wiktextract dump](https://kaikki.org/dictionary/rawdata.html) | English inflected forms, IPA, Polish translation tables | Wiktionary contributors | CC BY-SA 4.0 | kaikki.org raw dump, published 2026-10-30 |

Individual entries correspond to the Wiktionary pages of the same title; the
page history on Wiktionary lists the authors of each page.

The Wiktionary data was extracted with Wiktextract:

> Tatu Ylonen. 2022. *Wiktextract: Wiktionary as Machine-Readable Structured
> Data.* In Proceedings of the 13th Language Resources and Evaluation
> Conference (LREC 2022), pages 1317–1325, Marseille, France.

## Changes made

Entries are selected, merged across both Wiktionaries, de-duplicated and
reformatted. English inflected forms are attached for lookup, inflections of
multi-word verbs are generated from their head verb ("give up" → "gave up"),
and short cross-references are added ("saw" → "see", lists of phrasal verbs
under their base verb).

## Tools

The `.mobi` files are compiled with
[kindling](https://github.com/ciscoriordan/kindling) (MIT licence), which is
downloaded at build time and not distributed with this repository.
