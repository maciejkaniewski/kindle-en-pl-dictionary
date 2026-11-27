# kindle-en-pl-dictionary

Free, open-source **English → Polish dictionary for Kindle** e-readers, built
from [Wiktionary](https://www.wiktionary.org/), with **phrasal verbs and
inflected forms that you can actually look up**: *gave up*, *woke up*,
*looked forward to*, *put up with*.

> 🇵🇱 **Po polsku:** darmowy słownik angielsko-polski do Kindle z czasownikami
> frazowymi. [Instrukcja instalacji po polsku ↓](#-po-polsku)

> **Status: early development.** A 32-entry pilot is being tested on a
> Kindle Paperwhite. The full dictionary (~100k headwords) is in progress and
> will be published under [Releases](../../releases).

## Why another dictionary?

Many Kindle dictionaries list phrasal verbs only *inside* the entry of the
base verb. The Kindle searches **only** the dictionary's index of headwords and
their inflected forms, so:

- selecting *gave up* finds nothing, because neither "give up" nor "gave up" is
  in the index;
- tapping *gave* opens *give*, but *give up* is buried at the end of a long
  entry that the popup does not show.

This dictionary fixes both:

| You do on the Kindle | You get |
|---|---|
| tap **gave** | *give*, with **give up · give in · give out …** listed at the top |
| select **gave up** / **giving up** | the *give up* entry |
| tap **saw** | *saw* (piła) **and** "→ see (czas przeszły)" |
| tap **children**, **went**, **woke** | *child*, *go*, *wake* |

## Installation

1. Download `kindle-en-pl-dictionary.mobi` from [Releases](../../releases)
   (not yet available, see Status).
2. Connect the Kindle by USB and copy the file into
   `documents/dictionaries/`. **Do not use Send-to-Kindle**: it converts the
   file and breaks dictionary lookup.
3. On the Kindle: **Settings → Language & Dictionaries → Dictionaries →
   English** → choose *Słownik angielsko-polski (Wiktionary)*.
4. In an English book, long-press a word, or drag-select a phrasal verb.

Recent Paperwhites (2024+) connect over MTP rather than as a USB drive. On
Linux, use your file manager (gvfs) or `jmtpfs`.

## Building from source

Requirements: Linux or macOS, Python 3.10+, `curl`, about 1 GB of disk space.

```sh
tools/download.sh   # Wiktionary extracts from kaikki.org (~670 MB) + kindling
make test-pilot     # build the pilot dictionary and run the lookup tests
```

The output is written to `build/pilot/en-pl-pilot.mobi`.

How it works:

1. `tools/extract.py` reads the kaikki.org Wiktionary extracts: Polish
   definitions from Polish Wiktionary, English inflected forms and Polish
   translations from English Wiktionary.
2. `tools/build.py` merges them per headword, generates the inflections of
   multi-word verbs, resolves form/headword collisions, writes Kindle OPF/XHTML
   and compiles a `.mobi` with
   [kindling](https://github.com/ciscoriordan/kindling).
3. `tools/check_lookups.py` uses kindling's on-device lookup simulator to check
   that, for example, *gave up* opens *give up* (`tests/lookups_pilot.tsv`).

## Roadmap

- [x] Pilot: 32 entries, phrasal verbs, inflections, collision handling
- [ ] Device test on a Kindle Paperwhite (tap and multi-word selection)
- [ ] Full build from the complete Wiktionary data (~100k headwords)
- [ ] GitHub Actions: build, test and publish releases
- [ ] Fill gaps for missing phrasal verbs and idioms
- [ ] Optional: Polish → English, and StarDict for KOReader / Kobo

## License

- **Dictionary content:** [CC BY-SA 4.0](LICENSE-DATA), derived from
  Wiktionary. See [ATTRIBUTION.md](ATTRIBUTION.md).
- **Code:** [MIT](LICENSE).

---

## 🇵🇱 Po polsku

Darmowy, otwarty **słownik angielsko-polski do czytników Kindle**, zbudowany z
danych Wikisłownika i Wiktionary. W odróżnieniu od wielu słowników wyszukuje
**czasowniki frazowe** (*give up*, *put up with*, *look forward to*) również w
formach odmienionych (*gave up*, *giving up*). Pod każdym czasownikiem
podstawowym jest lista jego czasowników frazowych.

> **Status:** wczesna wersja. Pilot (32 hasła) jest testowany na Kindle
> Paperwhite, a pełny słownik powstaje.

### Instalacja

1. Pobierz plik `kindle-en-pl-dictionary.mobi` z zakładki
   [Releases](../../releases).
2. Podłącz Kindle kablem USB i skopiuj plik do folderu
   `documents/dictionaries/`. **Nie używaj Send-to-Kindle**, bo psuje słowniki.
3. Na Kindle: **Ustawienia → Język i słowniki → Słowniki → angielski** →
   wybierz *Słownik angielsko-polski (Wiktionary)*.
4. W angielskiej książce przytrzymaj palec na słowie albo zaznacz całe
   wyrażenie, np. *gave up*.

Treść słownika jest dostępna na licencji CC BY-SA 4.0 (autorzy: społeczność
Wikisłownika i Wiktionary), a kod na licencji MIT.
