# kindle-en-pl-dictionary

Free, open-source **English → Polish dictionary for Kindle** e-readers, built
from [Wiktionary](https://www.wiktionary.org/), with **phrasal verbs and
inflected forms that you can actually look up**: *gave up*, *woke up*,
*looked forward to*, *put up with*.

> 🇵🇱 **Po polsku:** darmowy słownik angielsko-polski na czytniki Kindle, który
> rozpoznaje czasowniki frazowe. [Opis i instrukcja instalacji ↓](#-po-polsku)

> **Status: early development.** The full dictionary (108,000 entries,
> 124,000 inflected forms) builds and passes 171 automated lookup tests. It is
> now being tested on a Kindle Paperwhite. There is no release yet; it will be
> published under [Releases](../../releases).

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

Requirements: Linux or macOS, Python 3.10+, `curl`, about 4 GB of disk space.

```sh
tools/download.sh   # Wiktionary data from kaikki.org (~3.2 GB) + kindling
make test           # build the full dictionary (~5 min) and run the lookup tests
```

The output is written to `build/full/kindle-en-pl-dictionary.mobi`.
`make test-pilot` builds a small 32-entry dictionary from `pilot/words.txt`.

How it works:

1. `tools/extract.py` reads the kaikki.org Wiktionary extracts: Polish
   definitions from Polish Wiktionary, English inflected forms and Polish
   translations from English Wiktionary.
2. `tools/build.py` merges them per headword, generates the inflections of
   multi-word verbs, resolves form/headword collisions, writes Kindle OPF/XHTML
   and compiles a `.mobi` with
   [kindling](https://github.com/ciscoriordan/kindling).
3. `tools/check_lookups.py` uses kindling's on-device lookup simulator to check
   that, for example, *gave up* opens *give up* (`tests/lookups.tsv`).

## Roadmap

- [x] Pilot: 32 entries, phrasal verbs, inflections, collision handling
- [x] Full build from the complete Wiktionary data (108k entries)
- [ ] Device test on a Kindle Paperwhite (tap and multi-word selection)
- [ ] GitHub Actions: build, test and publish releases
- [ ] Fill gaps for missing phrasal verbs and idioms
- [ ] Optional: Polish → English, and StarDict for KOReader / Kobo

## License

- **Dictionary content:** [CC BY-SA 4.0](LICENSE-DATA), derived from
  Wiktionary. See [ATTRIBUTION.md](ATTRIBUTION.md).
- **Code:** [MIT](LICENSE).

---

## 🇵🇱 Po polsku

Darmowy, otwarty **słownik angielsko-polski na czytniki Kindle**, oparty na
danych z polskiego i angielskiego Wikisłownika. W przeciwieństwie do wielu
innych słowników znajdziesz w nim **czasowniki frazowe** (*give up*, *put up
with*, *look forward to*), także w formie odmienionej (*gave up*, *giving
up*). Hasło każdego czasownika zaczyna się od listy powiązanych z nim
czasowników frazowych.

> **Status:** słownik jest na wczesnym etapie. Pełna wersja (108 tys. haseł)
> jest gotowa i przechodzi automatyczne testy, a teraz sprawdzamy ją na Kindle
> Paperwhite. Pierwsze wydanie pojawi się w zakładce Releases.

### Instalacja

1. Pobierz plik `kindle-en-pl-dictionary.mobi` z zakładki
   [Releases](../../releases).
2. Podłącz czytnik do komputera kablem USB i skopiuj plik do folderu
   `documents/dictionaries/`. **Nie wysyłaj go przez Send to Kindle**: usługa
   konwertuje plik i słownik przestaje działać.
3. Na czytniku wejdź w **Settings → Language & Dictionaries → Dictionaries →
   English** i wybierz *Słownik angielsko-polski (Wiktionary)*.
4. Otwórz książkę po angielsku i przytrzymaj palec na słowie albo zaznacz
   całe wyrażenie, np. *gave up*.

Treść słownika jest udostępniona na licencji CC BY-SA 4.0 (autorzy:
społeczności polskiego i angielskiego Wikisłownika), a kod źródłowy na
licencji MIT.
