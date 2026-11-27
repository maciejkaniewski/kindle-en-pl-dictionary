#!/usr/bin/env python3
"""Extract English->Polish dictionary records from kaikki.org (wiktextract) dumps.

Reads:
  * Polish Wiktionary extract (pl-extract.jsonl.gz): English entries with Polish
    glosses, examples and register labels.  This is the backbone.
  * English Wiktionary extract (kaikki-English.jsonl.gz): English inflected forms,
    IPA and Polish translation tables.

Writes one normalised JSON record per (source, headword, part of speech) to a
JSONL file consumed by tools/build.py.  No merging happens here.

Record schema:
  {"hw": str, "src": "plwikt"|"enwikt", "pos": str, "pos_label": str,
   "ipa": str|None, "phrasal": bool,
   "senses": [{"gloss": str, "labels": [str], "en": str|None,
               "examples": [[en, pl], ...]}],
   "forms": [[form, [tags]]],          # inflected forms of this headword
   "form_of": [[lemma, [tags]]],       # this headword is an inflection of lemma
   "n_langs": int}                     # (English Wiktionary only) number of languages
                                       # it is translated into, a popularity proxy
"""
import argparse
import gzip
import json
import re
import sys

# --- Polish labels -----------------------------------------------------------

POS_PL = {
    "verb": "czasownik", "noun": "rzeczownik", "adj": "przymiotnik",
    "adv": "przysłówek", "prep": "przyimek", "pron": "zaimek",
    "conj": "spójnik", "intj": "wykrzyknik", "det": "określnik",
    "num": "liczebnik", "particle": "partykuła", "phrase": "wyrażenie",
    "prep_phrase": "wyrażenie przyimkowe", "proverb": "przysłowie", "adv_phrase": "wyrażenie przysłówkowe",
    "article": "przedimek", "contraction": "forma ściągnięta",
    "abbrev": "skrót", "name": "nazwa własna",
}

# English Wiktionary sense/translation tags and Polish Wiktionary tags ->
# conventional Polish dictionary abbreviations.
LABELS_PL = {
    "colloquial": "pot.", "informal": "pot.", "British-English": "bryt.",
    "British": "bryt.", "UK": "bryt.", "US": "amer.", "slang": "slang",
    "metaphoric": "przen.", "figuratively": "przen.", "dated": "przest.",
    "obsolete": "daw.", "vulgar": "wulg.", "rare": "rzad.",
    "pejorative": "pejor.", "derogatory": "pejor.", "literary": "książk.",
    "offensive": "obraźl.", "humorous": "żart.", "poetic": "poet.",
    "formal": "form.", "euphemistic": "eufem.", "Canadian-English": "kanad.",
    "Irish": "irl.", "archaic": "arch.", "dialectal": "gw.",
    "diminutive": "zdrobn.", "childish": "dziec.", "ironic": "iron.",
    "Biblical": "bibl.", "neologism": "neol.", "literally": "dosł.",
    "Australian": "austral.", "Scotland": "szkoc.", "officially": "oficj.",
}

# Polish Wiktionary abbreviates phrase types ("fraza rzeczownikowa" -> "rzeczownikowa").
PL_POS_FIX = {
    "rzeczownikowa": "wyrażenie rzeczownikowe", "przymiotnikowa": "wyrażenie przymiotnikowe",
    "przysłówkowa": "wyrażenie przysłówkowe", "wykrzyknikowa": "wyrażenie wykrzyknikowe",
    "przyimkowa": "wyrażenie przyimkowe", "czasownikowa": "wyrażenie czasownikowe",
    "liczebnikowa": "wyrażenie liczebnikowe", "partykułowa": "wyrażenie partykułowe",
    "fraza": "wyrażenie", "przysłowie angielskie": "przysłowie",
}

# Parts of speech we leave out: affixes, letters, symbols.
SKIP_POS_PL = {"przedrostek", "przyrostek", "międzyrostek", "słowotwórczy",
               "litera", "symbol", "znak interpunkcyjny", "unknown", "czasownika", "zaimka"}
SKIP_POS_EN = {"prefix", "suffix", "infix", "interfix", "affix", "circumfix",
               "character", "symbol", "punct", "romanization"}

# Inflected-form tags we never index (spelling variants, dead forms, template noise).
BAD_FORM_TAGS = {
    "obsolete", "archaic", "dialectal", "nonstandard", "misspelling",
    "alternative", "rare", "table-tags", "inflection-template", "class",
    "romanization", "pronunciation-spelling", "canonical", "Early-Modern",
    "Middle-English", "error-unrecognized-form", "colloquial", "slang",
    "eye-dialect", "uncommon",
}

# Particles/prepositions that can follow a verb in a phrasal verb.
PARTICLES = {
    "about", "across", "after", "against", "ahead", "along", "apart", "around",
    "aside", "at", "away", "back", "behind", "by", "down", "for", "forth",
    "forward", "from", "in", "into", "of", "off", "on", "onto", "out", "over",
    "past", "round", "through", "to", "together", "under", "up", "upon", "with",
    "without",
}

# Polish Wiktionary glosses that only say "inflected form of X" — we build those
# links ourselves from English Wiktionary form data.
PL_FORM_GLOSS = re.compile(
    r"^(forma |imiesłów |lm od|l\.\s?mn\. od|liczba mnoga od|stopień (wyższy|najwyższy) od|"
    r"3\. os|trzecia osoba|czas przeszły od)", re.I)

# Words in English Wiktionary translation entries sometimes carry aspect markers.
ASPECT = re.compile(r"\s+\b(impf|pf)\b\.?\s*")


def fix_parens(text):
    """Repair brackets lost in extraction: "On) podarł" -> "(On) podarł"."""
    text = text.strip()
    if text.count(")") == text.count("(") + 1 and text.find(")") < (text.find("(") % (len(text) + 1)):
        text = "(" + text
    if text.count("(") == text.count(")") + 1 and text.rfind("(") > text.rfind(")"):
        text = text + ")"
    if text.count('"') % 2 == 1 and not text.startswith('"') and 0 < text.find('"') < 40:
        text = '"' + text  # 'Allah" jest ...' -> '"Allah" jest ...'
    if text.count("\u201d") > text.count("\u201c") + text.count("\u201e") and 0 < text.find("\u201d") < 40:
        text = "\u201e" + text  # 'Allah” jest' -> '„Allah” jest'
    return text


def open_text(path):
    return gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")


def looks_phrasal(hw):
    parts = hw.split()
    return len(parts) >= 2 and all(p in PARTICLES for p in parts[1:])


def labels_from(tags, raw_tags=()):
    out = []
    for t in tags or ():
        lab = LABELS_PL.get(t)
        if lab and lab not in out:
            out.append(lab)
    for t in raw_tags or ():
        if t.endswith(".") and t not in out:
            out.append(t)
    return out


def clean_form(form, hw, tags):
    if not form or form == "-":
        return None  # forms equal to the headword are kept: "put (put, put)"
    if set(tags) & BAD_FORM_TAGS:
        return None
    if form.startswith(("more ", "most ")) or any(c in form for c in "()[]/,;"):
        return None
    if " " in form and " " not in hw:
        return None  # periphrastic forms like "further left"
    return form


# --- Polish Wiktionary --------------------------------------------------------

def extract_plwikt(path, wanted):
    with open_text(path) as f:
        for line in f:
            if '"lang_code": "en"' not in line:
                continue
            d = json.loads(line)
            if d.get("lang_code") != "en":
                continue
            hw = d.get("word")
            if not hw or (wanted is not None and hw not in wanted):
                continue
            pos_label = d.get("pos_title") or POS_PL.get(d.get("pos"), d.get("pos") or "")
            if pos_label in SKIP_POS_PL:
                continue
            pos_label = PL_POS_FIX.get(pos_label, pos_label)
            senses, form_of = [], []
            for s in d.get("senses", []):
                glosses = [fix_parens(g) for g in s.get("glosses", []) if g.strip()]
                if not glosses:
                    continue
                gloss = "; ".join(glosses)
                if s.get("form_of") or PL_FORM_GLOSS.match(gloss):
                    if set(s.get("tags", [])) & BAD_FORM_TAGS:
                        continue  # e.g. "went" as obsolete past tense of "wend"
                    for fo in s.get("form_of") or ():
                        lemma = re.sub(r"^to ", "", fo.get("word", ""))
                        if lemma:
                            form_of.append([lemma, []])
                    continue
                examples = []
                for ex in s.get("examples", [])[:2]:
                    if ex.get("text") and ex.get("translation"):
                        examples.append([fix_parens(ex["text"]), fix_parens(ex["translation"])])
                senses.append({
                    "gloss": gloss,
                    "labels": labels_from(s.get("tags"), s.get("raw_tags")),
                    "en": None,
                    "examples": examples,
                })
            ipa = next((s["ipa"] for s in d.get("sounds", []) if s.get("ipa") and not s.get("tags")), None)
            if not senses and not form_of:
                continue
            yield {
                "hw": hw, "src": "plwikt", "pos": d.get("pos") or "",
                "pos_label": pos_label, "ipa": ipa,
                "phrasal": pos_label == "czasownik frazowy" or ("phrasal" in d.get("tags", [])),
                "senses": senses, "forms": [], "form_of": form_of,
            }


# --- English Wiktionary -------------------------------------------------------

def extract_enwikt(path, wanted):
    with open_text(path) as f:
        for line in f:
            if wanted is not None and not wanted_first(line, wanted):
                continue
            d = json.loads(line)
            hw = d.get("word")
            if not hw or (wanted is not None and hw not in wanted):
                continue
            if d.get("lang_code", "en") != "en" or d.get("pos") in SKIP_POS_EN:
                continue

            forms = []
            for fm in d.get("forms", []):
                tags = fm.get("tags", [])
                form = clean_form(fm.get("form", "").strip(), hw, tags)
                if form:
                    forms.append([form, tags])

            form_of = []
            for s in d.get("senses", []):
                if set(s.get("tags", [])) & BAD_FORM_TAGS:
                    continue  # e.g. "saw" as nonstandard past participle of "see"
                for fo in s.get("form_of", []) or ():
                    if fo.get("word"):
                        form_of.append([fo["word"], s.get("tags", [])])

            # Polish translations, grouped by the translation table's own sense
            # heading (kaikki's sense attachment is unreliable).
            groups = {}
            trs = list(d.get("translations", []))
            for s in d.get("senses", []):
                trs.extend(s.get("translations", []) or ())
            # Popularity proxy: common words and phrases are translated into
            # many languages ("go out": 92, "go forth": a handful).
            n_langs = len({t.get("lang_code") for t in trs if t.get("lang_code")})
            for t in trs:
                if t.get("lang_code") != "pl" or not t.get("word"):
                    continue
                word = ASPECT.sub(" / ", t["word"].strip()).strip(" /")
                word = re.sub(r"^(but )?see\s+", "", word)  # leaked "but see" cross-references
                if not word:
                    continue
                key = (t.get("sense") or "").strip()
                if key.lower().startswith("translations"):
                    key = ""  # table without its own gloss heading
                g = groups.setdefault(key, {"words": [], "labels": []})
                if word not in g["words"]:
                    g["words"].append(word)
                for lab in labels_from(t.get("tags")):
                    if lab not in g["labels"]:
                        g["labels"].append(lab)
            senses = [{"gloss": ", ".join(g["words"]), "labels": g["labels"],
                       "en": key or None, "examples": []} for key, g in groups.items()]

            ipa = None
            for snd in d.get("sounds", []):
                if snd.get("ipa"):
                    tags = snd.get("tags", [])
                    if ipa is None or "Received-Pronunciation" in tags or "UK" in tags:
                        ipa = snd["ipa"].strip("/[]")
                        if "Received-Pronunciation" in tags or "UK" in tags:
                            break

            def cat_names(items):
                return [c if isinstance(c, str) else c.get("name", "") for c in items or ()]
            cats = " ".join(cat_names(d.get("categories")) +
                            [c for s in d.get("senses", []) for c in cat_names(s.get("categories"))])
            phrasal = "phrasal verbs" in cats or (d.get("pos") == "verb" and looks_phrasal(hw))

            if not senses and not forms and not form_of:
                continue
            yield {
                "hw": hw, "src": "enwikt", "pos": d.get("pos") or "",
                "pos_label": POS_PL.get(d.get("pos"), d.get("pos") or ""),
                "ipa": ipa, "phrasal": phrasal, "senses": senses,
                "forms": forms, "form_of": form_of, "n_langs": n_langs,
            }


_WORD_KEY = re.compile(r'"word": "((?:[^"\\]|\\.)*)"')


def wanted_first(line, wanted):
    """Cheap pre-filter: candidate headwords mentioned anywhere in the line."""
    return [m for m in _WORD_KEY.findall(line) if m in wanted]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plwikt", required=True, help="kaikki Polish Wiktionary extract (.jsonl[.gz])")
    ap.add_argument("--enwikt", required=True, help="kaikki English Wiktionary extract (.jsonl[.gz])")
    ap.add_argument("--words", help="optional file with one headword per line (pilot builds)")
    ap.add_argument("-o", "--output", required=True, help="output JSONL")
    args = ap.parse_args()

    wanted = None
    if args.words:
        with open(args.words, encoding="utf-8") as f:
            wanted = {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}

    n = 0
    with open(args.output, "w", encoding="utf-8") as out:
        for extractor, path in ((extract_plwikt, args.plwikt), (extract_enwikt, args.enwikt)):
            for rec in extractor(path, wanted):
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
            print(f"{extractor.__name__}: done ({n} records so far)", file=sys.stderr)
    print(f"wrote {n} records to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
