# kindle-en-pl-dictionary

An **English → Polish dictionary for Kindle** e-readers, built from
[Wiktionary](https://www.wiktionary.org/).

> 🇵🇱 Słownik angielsko-polski na czytniki Kindle.
> [Opis i instrukcja instalacji ↓](#-po-polsku)

> **Status: early development.** The full dictionary (108,000 entries,
> 124,000 inflected forms) builds and passes 171 automated lookup tests. It is
> now being tested on a Kindle Paperwhite. There is no release yet; it will be
> published under [Releases](../../releases).

## Features

- **108,000 entries** with Polish definitions and example sentences from the
  Polish and English Wiktionary
- **Inflected forms:** tapping *went*, *children* or *better* opens *go*,
  *child* and *good*
- **Phrasal verbs as entries of their own**, inflected forms included:
  selecting *gave up* opens *give up*
- **Clean entries in the style of the Oxford Dictionary of English:**
  meanings with inline examples first, then the most common phrasal verbs and
  idioms of the word, each with a short translation
- **Words that are also inflections** show both meanings: *saw* gives *piła*
  and "→ see"

## How lookup works

The Kindle only searches a dictionary's index of headwords and their inflected
forms. A phrasal verb that appears only inside the entry of its base verb
cannot be found by selecting it, and the popup rarely shows the end of a long
entry. This dictionary therefore indexes phrasal verbs on their own and lists
the most common ones in the verb entry:

| You do on the Kindle | You get |
|---|---|
| tap **gave** | *give* (gave, given), with *give up, give back, give in…* in its phrasal-verb section |
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

## Corrections

The Polish text comes from Wiktionary and is sometimes clumsy. Corrections
live in [`corrections/polish.tsv`](corrections/polish.tsv), one row per change,
and are applied at build time once their status is `approved`. Suggestions made
with the help of AI are marked `ai` and stay `pending` until a person has
reviewed them.

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

Słownik angielsko-polski na czytniki Kindle, oparty na danych z polskiego i
angielskiego Wikisłownika.

### Funkcje

- **108 tys. haseł** z polskimi znaczeniami i przykładami użycia
- **Formy odmienione:** *went*, *children* czy *better* prowadzą do haseł
  *go*, *child* i *good*
- **Czasowniki frazowe jako osobne hasła**, także w formie odmienionej:
  zaznaczenie *gave up* otwiera hasło *give up*
- **Przejrzyste hasła wzorowane na Oxford Dictionary of English:** najpierw
  znaczenia z przykładami, potem najczęstsze czasowniki frazowe i idiomy danego
  słowa, każdy z krótkim tłumaczeniem

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
