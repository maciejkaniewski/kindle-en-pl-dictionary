#!/usr/bin/env python3
"""Build a Kindle English->Polish dictionary from records produced by extract.py.

Steps:
  1. merge records per headword (Polish Wiktionary senses first, then English
     Wiktionary translation groups that add new Polish words);
  2. collect inflected forms, generating them for multi-word verbs
     ("give up" -> "gave up", "giving up", ...);
  3. resolve collisions: a form that is also a headword ("saw", "left") or that
     belongs to several lemmas is NOT indexed as an inflection; instead its own
     entry starts with "→ see (czas przeszły)";
  4. list phrasal verbs / expressions at the top of the base verb's entry, so a
     tap on "gave" shows "give up · give in · ..." without scrolling;
  5. write OPF + XHTML and (optionally) compile with kindling.
"""
import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict

PARTICLES = {
    "about", "across", "after", "against", "ahead", "along", "apart", "around",
    "aside", "at", "away", "back", "behind", "by", "down", "for", "forth",
    "forward", "from", "in", "into", "of", "off", "on", "onto", "out", "over",
    "past", "round", "through", "to", "together", "under", "up", "upon", "with",
    "without",
}

POS_ORDER = ["verb", "noun", "adj", "adv", "pron", "prep", "conj", "det", "num",
             "intj", "particle", "phrase", "prep_phrase", "proverb"]

MAX_LIST = 5            # phrasal verbs / idioms listed under a headword (most common first)
MAX_EXAMPLES = 1        # examples shown per sense


def esc(s):
    return html.escape(s, quote=True)


def shorten(s, n):
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def form_desc(tags):
    t = set(tags)
    if "past" in t and "participle" in t:
        return "III forma"
    if "past" in t:
        return "czas przeszły"
    if "present" in t and "participle" in t:
        return "forma z -ing"
    if "third-person" in t or ("present" in t and "singular" in t):
        return "3. os. l. poj."
    if "plural" in t:
        return "l. mn."
    if "comparative" in t:
        return "st. wyższy"
    if "superlative" in t:
        return "st. najwyższy"
    return None


def form_pos(tags):
    t = set(tags)
    if t & {"past", "participle", "third-person", "present"}:
        return "verb"
    if "plural" in t:
        return "noun"
    if t & {"comparative", "superlative"}:
        return "adj"
    return None


class Entry:
    def __init__(self, hw):
        self.hw = hw
        self.ipa = None
        self.phrasal = False
        self.blocks = OrderedDict()   # pos -> {"label", "pl": [senses], "en": [senses]}
        self.forms = defaultdict(set)  # form -> set(tag tuples)
        self.form_of = OrderedDict()   # lemma -> set(desc)
        self.all_forms = []            # every (form, tags) of this lemma, for the header line
        self.popularity = 0            # languages it is translated into (English Wiktionary)

    def has_senses(self):
        return any(b["pl"] or b["en"] for b in self.blocks.values())

    def block(self, pos, label):
        b = self.blocks.get(pos)
        if b is None:
            b = self.blocks[pos] = {"label": label, "pl": [], "en": []}
        return b

    def first_gloss(self, pos=None):
        order = ([pos] if pos in self.blocks else []) + list(self.blocks)
        for p in order:
            b = self.blocks[p]
            for s in b["pl"] + b["en"]:
                return s["gloss"]
        return None


def apply_corrections(r, corrections, used):
    """Replace Polish text that has an approved correction (corrections/polish.tsv)."""
    hw = r["hw"]
    for s in r["senses"]:
        key = (hw, s["gloss"])
        if key in corrections:
            s["gloss"] = corrections[key]
            used.add(key)
        examples = []
        for en, pl in s["examples"]:
            key = (hw, pl)
            if key in corrections:
                used.add(key)
                if corrections[key] == "-":
                    continue  # example removed
                pl = corrections[key]
            examples.append([en, pl])
        s["examples"] = examples


def load(records_path, corrections=None):
    entries = {}
    lemma_forms = defaultdict(list)   # lemma -> [(form, tags)]
    form_of_recs = []                 # (form, lemma, tags)
    corrections = corrections or {}
    used = set()
    for line in open(records_path, encoding="utf-8"):
        r = json.loads(line)
        if corrections:
            apply_corrections(r, corrections, used)
        e = entries.setdefault(r["hw"], Entry(r["hw"]))
        if r["ipa"] and (e.ipa is None or r["src"] == "plwikt"):
            e.ipa = r["ipa"]
        e.phrasal = e.phrasal or r["phrasal"]
        e.popularity = max(e.popularity, r.get("n_langs", 0))
        if r["senses"]:
            label = r["pos_label"]
            pos = r["pos"] or label
            b = e.block(pos, label)
            if r["src"] == "plwikt":
                b["label"] = label  # Polish Wiktionary label wins ("czasownik frazowy")
                b["pl"].extend(r["senses"])
            else:
                b["en"].extend(r["senses"])
        for form, tags in r["forms"]:
            lemma_forms[r["hw"]].append((form, tuple(tags)))
        for lemma, tags in r["form_of"]:
            form_of_recs.append((r["hw"], lemma, tuple(tags)))
    return entries, lemma_forms, form_of_recs, used


POSSESSIVES = ["my", "your", "his", "her", "its", "our", "their"]
REFLEXIVES = ["myself", "yourself", "himself", "herself", "itself", "ourselves", "yourselves", "themselves"]


def expand_placeholders(phrase):
    """"make up one's mind" -> "make up my mind", "make up his mind", ...

    Headwords with placeholders never occur verbatim in books; their real
    variants are indexed as inflected forms instead.
    """
    variants = [[]]
    for tok in phrase.replace("\u2019", "'").split(" "):
        if tok in ("one's", "someone's", "somebody's"):
            opts = POSSESSIVES
        elif tok == "oneself":
            opts = REFLEXIVES
        else:
            opts = [tok]
        variants = [v + [o] for v in variants for o in opts]
    return [" ".join(v) for v in variants] if len(variants) > 1 else []


def verb_forms(lemma, lemma_forms):
    """Inflected forms of a single-word verb, keyed by tag tuple."""
    out = []
    for form, tags in lemma_forms.get(lemma, ()):
        if form_pos(tags) == "verb" and " " not in form:
            out.append((form, tags))
    return out


def merge(entries, lemma_forms, form_of_recs):
    headwords = {hw for hw, e in entries.items() if e.has_senses()}

    # 1. generate inflections of multi-word verbs from their head verb
    for hw in headwords:
        e = entries[hw]
        parts = hw.split(" ")
        if len(parts) < 2 or "verb" not in e.blocks:
            continue
        for form, tags in verb_forms(parts[0], lemma_forms):
            lemma_forms[hw].append((" ".join([form] + parts[1:]), tags))

    for hw in headwords:
        if " " not in hw:
            continue
        extra = [(v, ()) for v in expand_placeholders(hw)]
        for form, tags in list(lemma_forms.get(hw, ())):
            extra += [(v, tags) for v in expand_placeholders(form)]
        lemma_forms[hw].extend(extra)

    # 2. form -> lemmas
    form_lemmas = defaultdict(lambda: defaultdict(set))
    for lemma in headwords:
        for form, tags in lemma_forms.get(lemma, ()):
            if form != lemma:
                form_lemmas[form][lemma].add(tags)
    for form, lemma, tags in form_of_recs:
        lemma = re.sub(r"^to ", "", lemma)
        if lemma in headwords and form != lemma:
            form_lemmas[form][lemma].add(tags)

    for lemma in headwords:
        entries[lemma].all_forms = list(lemma_forms.get(lemma, ()))

    # 3. attach forms: plain inflection, or "→ lemma" line on a separate entry
    collisions = 0
    hw_lower = {h.lower() for h in headwords}
    for form, lemmas in form_lemmas.items():
        if form.lower() in hw_lower or len(lemmas) > 1:
            target = entries.setdefault(form, Entry(form))
            for lemma, tagsets in lemmas.items():
                descs = target.form_of.setdefault(lemma, set())
                for tags in tagsets:
                    d = form_desc(tags)
                    if d:
                        descs.add(d)
            collisions += 1
        else:
            (lemma, tagsets), = lemmas.items()
            for tags in tagsets:
                entries[lemma].forms[form].add(tags)

    final = {hw: e for hw, e in entries.items() if e.has_senses() or e.form_of}

    # 4. fold spellings that differ only in case ("may" + "May", "polish" +
    #    "Polish") into one entry: the Kindle prefers an exact-case match, so a
    #    sentence-initial "May" would otherwise open the month, not the verb.
    groups = defaultdict(list)
    for hw in final:
        groups[hw.lower()].append(hw)
    for variants in groups.values():
        if len(variants) < 2:
            continue
        variants.sort(key=lambda h: (h != h.lower(), h))
        primary = final[variants[0]]
        for v in variants[1:]:
            e = final.pop(v)
            known = {s["gloss"] for b in primary.blocks.values() for s in b["pl"] + b["en"]}
            for pos, b in e.blocks.items():
                # drop senses the primary spelling already has ("YOLO" vs "yolo")
                pl = [s for s in b["pl"] if s["gloss"] not in known]
                en = [s for s in b["en"] if s["gloss"] not in known]
                if pl or en:
                    primary.blocks[f"{v}|{pos}"] = dict(b, pl=pl, en=en, variant=v)
            for f, t in e.forms.items():
                primary.forms[f] |= t
            for lemma, d in e.form_of.items():
                primary.form_of.setdefault(lemma, set()).update(d)
            primary.ipa = primary.ipa or e.ipa
    by_lower = {hw.lower(): hw for hw in final}

    # 5. phrasal verbs and expressions under their first word
    phrasal_of = defaultdict(list)
    expr_of = defaultdict(list)
    for hw in headwords:
        parts = hw.split(" ")
        base = by_lower.get(parts[0].lower())
        if len(parts) < 2 or base is None or hw not in final:
            continue
        is_pv = all(p in PARTICLES for p in parts[1:]) and ("verb" in entries[hw].blocks or entries[hw].phrasal)
        (phrasal_of if is_pv else expr_of)[base].append(hw)
    return final, phrasal_of, expr_of, collisions, by_lower


# --- rendering ----------------------------------------------------------------

DESC_ORDER = ["czas przeszły", "III forma", "forma z -ing", "3. os. l. poj.", "l. mn.", "st. wyższy", "st. najwyższy"]


QUALIFIER = re.compile(r"^([^:;,()]{2,40}):\s+(?=\S)")


def render_gloss(gloss):
    """Italicise a leading usage note such as 'w brydżu:' or 'o człowieku:'."""
    m = QUALIFIER.match(gloss)
    if m and len(m.group(1).split()) <= 5:
        return f"<i>{esc(m.group(1))}:</i> {esc(gloss[m.end():])}"
    return esc(gloss)


EXAMPLE_SENSES = 3      # only the first meanings of an entry get an example
VULGAR = re.compile(r"\b(fuck\w*|shit\w*|cunt|dick|cock|piss\w*|bitch\w*|turd|arse|ass|crap)\b", re.I)


def idiom_list(expressions, entries):
    """Idioms to list under a headword: no vulgar ones, those from Polish
    Wiktionary (curated, usually common) first."""
    def curated(hw):
        e = entries.get(hw)
        return bool(e) and any(b["pl"] for b in e.blocks.values())

    def offensive(hw):
        e = entries.get(hw)
        return bool(VULGAR.search(hw)) or bool(e) and any(
            set(s["labels"]) & {"wulg.", "obraźl."} for b in e.blocks.values() for s in b["pl"] + b["en"])
    # long proverbs stay searchable, but would clutter the list
    keep = [x for x in expressions if not offensive(x) and len(x.split()) <= 6]
    return sorted(keep, key=lambda x: (-popularity(entries, x), not curated(x), x.lower()))


def popularity(entries, hw):
    e = entries.get(hw)
    return e.popularity if e else 0
SPACER = "<div>&#160;</div>"


def clean_ipa(ipa):
    """Drop tie bars (t͡ʃ -> tʃ): the Kindle font renders them as a box."""
    return ipa.strip("/").replace("\u0361", "").replace("\u035c", "")


def prepare_blocks(e):
    """Return (key, block, senses) in display order.

    English Wiktionary translations whose Polish words already appear anywhere
    in the entry's Polish Wiktionary text are dropped, so a meaning is never
    shown twice ("break the ice": czasownik + wyrażenie with the same gloss).
    Blocks are ordered by number of meanings ("mouse": noun before verb), with
    folded capitalised variants ("May" in "may") last.
    """
    pl_text = " ".join(s["gloss"] for b in e.blocks.values() for s in b["pl"]).lower()
    prepared = []
    for key, b in e.blocks.items():
        en = []
        for s in b["en"]:
            words = [w.strip() for w in s["gloss"].split(",") if w.strip()]
            new = [w for w in words if w.lower() not in pl_text]
            if new:
                pl_text += " " + " ".join(new).lower()
                en.append(dict(s, gloss=", ".join(new)))
        senses = b["pl"] + en
        if senses:
            prepared.append((key, b, senses))

    def order(item):
        key, b, senses = item
        pos = key.split("|")[-1]
        return (bool(b.get("variant")), -len(senses),
                POS_ORDER.index(pos) if pos in POS_ORDER else len(POS_ORDER))
    return sorted(prepared, key=order)


POS_ABBR = {
    "czasownik": "czas.", "czasownik frazowy": "czas. fraz.", "rzeczownik": "rzecz.",
    "przymiotnik": "przym.", "przysłówek": "przysł.", "zaimek": "zaim.", "zaimek osobowy": "zaim.",
    "zaimek pytajny": "zaim.", "przyimek": "przyim.", "spójnik": "spój.", "wykrzyknik": "wykrz.",
    "liczebnik": "licz.", "liczebnik główny": "licz.", "liczebnik porządkowy": "licz.",
    "określnik": "określ.", "partykuła": "part.", "przedimek": "przedim.", "nazwa własna": "nazwa wł.",
    "wyrażenie": "wyr.", "wyrażenie rzeczownikowe": "wyr.", "wyrażenie przymiotnikowe": "wyr.",
    "wyrażenie przysłówkowe": "wyr.", "wyrażenie przyimkowe": "wyr.", "wyrażenie wykrzyknikowe": "wyr.",
    "wyrażenie czasownikowe": "wyr.", "związek frazeologiczny": "frazeol.",
}


def header_forms(e, pos):
    """Irregular forms for the part-of-speech line: "(gave, given)", "(l. mn. children)"."""
    def first(pred):
        return next((f for f, t in e.all_forms if pred(set(t))), None)
    if pos == "verb":
        past = first(lambda t: "past" in t and "participle" not in t)
        pp = first(lambda t: "past" in t and "participle" in t)
        if past and pp and not (past.endswith("ed") and pp.endswith("ed")):
            return f" (<b>{esc(past)}</b>, <b>{esc(pp)}</b>)" if past != pp else f" (<b>{esc(past)}</b>)"
    elif pos == "noun":
        verbal = {"past", "present", "participle", "first-person", "second-person", "third-person", "subjunctive"}
        pl = first(lambda t: "plural" in t and not t & verbal)  # not "past plural" of old verb tables
        hw = e.hw
        regular = {hw + "s", hw + "es"} | ({hw[:-1] + "ies"} if hw.endswith("y") else set())
        if pl and pl not in regular:
            return f" (l. mn. <b>{esc(pl)}</b>)"
    return ""


def short_gloss(entries, hw, n=60):
    e = entries.get(hw)
    g = e.first_gloss() if e else None
    return f" – {esc(shorten(g, n))}" if g else ""


def render_entry(e, entries, phrasal_of, expr_of, by_lower):
    """Layout modelled on the Oxford Dictionary of English on Kindle:

        give /ɡɪv/
        ▪ czas. (gave, given) 1 dawać, przekazywać: My parents gave me a bicycle. – Moi rodzice…
        2 zaprezentować publicznie
        CZASOWNIKI FRAZOWE
        give up – porzucić, rzucić
        IDIOMY I ZWROTY
        give way – ustąpić
    """
    iforms = sorted(f for f in e.forms if f.lower() != e.hw.lower())
    infl = ""
    if iforms:
        infl = "<idx:infl>" + "".join(f'<idx:iform value="{esc(f)}"/>' for f in iforms) + "</idx:infl>"
    head = f'<idx:orth value="{esc(e.hw)}"><b>{esc(e.hw)}</b>{infl}</idx:orth>'
    if e.ipa:
        head += f" /{esc(clean_ipa(e.ipa))}/"
    body = [f"<div>{head}</div>"]

    # "saw" -> "→ see (czas przeszły): widzieć"
    for lemma, descs in e.form_of.items():
        d = ", ".join(sorted(descs, key=lambda x: DESC_ORDER.index(x) if x in DESC_ORDER else 99))
        pos = "verb" if descs & {"czas przeszły", "III forma", "forma z -ing", "3. os. l. poj."} else (
            "noun" if "l. mn." in descs else None)
        target = by_lower.get(lemma.lower())
        gloss = entries[target].first_gloss(pos) if target else None
        line = f"→ <b>{esc(lemma)}</b>"
        if d:
            line += f" <i>({esc(d)})</i>"
        if gloss:
            line += f": {esc(shorten(gloss, 70))}"
        body.append(f"<div>{line}</div>")

    blocks = prepare_blocks(e)

    # Capitalised variants folded into this entry ("Polish" in "polish") get a
    # one-line summary near the top, so the popup shows both meanings.
    seen = set()
    for _, block, senses in blocks:
        v = block.get("variant")
        if v and v not in seen:
            seen.add(v)
            body.append(f"<div><b>{esc(v)}</b> <i>({esc(block['label'])})</i>: "
                        f"{esc(shorten(senses[0]['gloss'], 70))}</div>")

    meaning_no = 0  # meanings shown so far in the whole entry
    for key, block, senses in blocks:
        pos = key.split("|")[-1]
        abbr = esc(POS_ABBR.get(block["label"], block["label"]))
        # The part-of-speech marker shares a line with the first meaning, so a
        # Kindle page break can never leave a bare "▪ czas." at the bottom.
        if block.get("variant"):
            marker = f"▪ <b>{esc(block['variant'])}</b> <i>{abbr}</i> "
        else:
            marker = f"▪ <i>{abbr}</i>{header_forms(e, pos)} "
        numbered = len(senses) > 1
        for n, s in enumerate(senses, 1):
            meaning_no += 1
            num = (marker if n == 1 else "") + (f"{n} " if numbered else "")
            labels = f"<i>{esc(', '.join(s['labels']))}</i> " if s["labels"] else ""
            line = f"{num}{labels}{render_gloss(s['gloss'])}"
            if meaning_no <= EXAMPLE_SENSES:  # examples only for the main meanings
                examples = " | ".join(f"<i>{esc(en)}</i> – {esc(pl)}" for en, pl in s["examples"][:MAX_EXAMPLES])
                if examples:
                    line += f": {examples}"
            body.append(f"<div>{line}</div>")

    def section(title, items):
        """The most common items with a short meaning; the rest stay searchable."""
        shown = items[:MAX_LIST]
        lines = [f"<div><b>{esc(p)}</b>{short_gloss(entries, p)}</div>" for p in shown]
        if len(items) > len(shown):
            lines.append(f"<div><i>… i {len(items) - len(shown)} więcej: zaznacz całe wyrażenie</i></div>")
        body.append(SPACER)
        body.append(f"<div><b>{title}</b></div>")
        body.extend(lines)

    # most common first (popularity proxy), then curated, then alphabetical
    pv = sorted(phrasal_of.get(e.hw, []), key=lambda p: (-popularity(entries, p), p.lower()))
    if pv:
        section("CZASOWNIKI FRAZOWE", pv)
    ex = idiom_list(expr_of.get(e.hw, []), entries)
    if ex:
        section("IDIOMY I ZWROTY", ex)

    return '<idx:entry name="default" scriptable="yes" spell="yes">\n' + "\n".join(body) + "\n</idx:entry>\n"


# --- package ------------------------------------------------------------------

XHTML_HEAD = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns:idx="http://www.mobipocket.com/idx" xmlns:mbp="http://www.mobipocket.com/mbp">
<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/><title>{title}</title></head>
<body>
"""


def write_package(outdir, title, entries_html, meta):
    os.makedirs(outdir, exist_ok=True)
    for old in os.listdir(outdir):  # stale chunks from a previous, larger build
        if re.fullmatch(r"content\d+\.html", old):
            os.remove(os.path.join(outdir, old))
    files = []
    chunk, size, idx = [], 0, 0

    def flush():
        nonlocal chunk, size, idx
        if not chunk:
            return
        name = f"content{idx:03d}.html"
        with open(os.path.join(outdir, name), "w", encoding="utf-8") as f:
            f.write(XHTML_HEAD.format(title=esc(title)))
            f.write("<mbp:frameset>\n")
            f.writelines(chunk)
            f.write("</mbp:frameset>\n</body>\n</html>\n")
        files.append(name)
        chunk, size, idx = [], 0, idx + 1

    for h in entries_html:
        chunk.append(h)
        size += len(h.encode("utf-8"))
        if size > 250_000:
            flush()
    flush()

    today = meta["date"]
    with open(os.path.join(outdir, "usage.html"), "w", encoding="utf-8") as f:
        f.write(XHTML_HEAD.format(title="Jak korzystać ze słownika") + f"""<h1>{esc(title)}</h1>
<p>Słownik angielsko-polski oparty na otwartych danych z polskiego i angielskiego Wikisłownika (pl.wiktionary.org, en.wiktionary.org).</p>
<h2>Jak korzystać ze słownika</h2>
<p><b>Pojedyncze słowa.</b> Przytrzymaj palec na słowie. Formy odmienione, np. <i>gave</i>, <i>went</i> czy <i>children</i>, prowadzą do hasła z formą podstawową.</p>
<p><b>Czasowniki frazowe i idiomy.</b> Zaznacz palcem całe wyrażenie, np. <i>gave up</i>, <i>put up with</i> albo <i>broke the ice</i>. Pod hasłem czasownika wymieniono jego najczęstsze czasowniki frazowe i idiomy; pozostałe znajdziesz, zaznaczając całe wyrażenie. Jeśli czasownik i partykułę rozdzielają inne słowa (<i>gave it up</i>), przytrzymaj palec na samym czasowniku.</p>
<p><b>Słownik domyślny.</b> Na czytniku wejdź w Settings → Language &amp; Dictionaries → Dictionaries → English i wybierz ten słownik.</p>
<h2>Skróty</h2>
<p><b>Części mowy:</b> czas. – czasownik • czas. fraz. – czasownik frazowy • rzecz. – rzeczownik • przym. – przymiotnik • przysł. – przysłówek • zaim. – zaimek • przyim. – przyimek • spój. – spójnik • wykrz. – wykrzyknik • licz. – liczebnik • wyr. – wyrażenie • frazeol. – związek frazeologiczny • nazwa wł. – nazwa własna</p>
<p><b>Kwalifikatory:</b> amer. – amerykański • arch. – archaiczny • bryt. – brytyjski • daw. – dawniej • dosł. – dosłownie • eufem. – eufemistyczny • form. – formalny • gw. – gwarowy • iron. – ironiczny • książk. – książkowy • l. mn. – liczba mnoga • obraźl. – obraźliwy • oficj. – oficjalny • pejor. – pejoratywny • poet. – poetycki • pot. – potoczny • przen. – przenośnie • przest. – przestarzały • rzad. – rzadki • st. wyższy, st. najwyższy – stopień wyższy, najwyższy • wulg. – wulgarny • zdrobn. – zdrobnienie • żart. – żartobliwy • 3. os. l. poj. – 3. osoba liczby pojedynczej • III forma – imiesłów czasu przeszłego (past participle) • forma z -ing – imiesłów czynny (present participle)</p>
</body></html>
""")
    with open(os.path.join(outdir, "copyright.html"), "w", encoding="utf-8") as f:
        f.write(XHTML_HEAD.format(title="Licencja i źródła") + f"""<h1>Licencja i źródła</h1>
<p>Treść słownika jest udostępniona na licencji Creative Commons Uznanie autorstwa – Na tych samych warunkach 4.0 Międzynarodowe (CC BY-SA 4.0): https://creativecommons.org/licenses/by-sa/4.0/deed.pl</p>
<p>Możesz ją kopiować, zmieniać i rozpowszechniać, także w celach komercyjnych, pod warunkiem że podasz autorów i udostępnisz swoją wersję na tej samej licencji.</p>
<h2>Źródła</h2>
<p>• Polski Wikisłownik (pl.wiktionary.org) – autorzy: społeczność Wikisłownika</p>
<p>• Angielski Wikisłownik (en.wiktionary.org) – autorzy: społeczność Wiktionary</p>
<p>Dane z obu serwisów wyodrębniono narzędziem Wiktextract (kaikki.org): Tatu Ylonen, „Wiktextract: Wiktionary as Machine-Readable Structured Data”, LREC 2022.</p>
<h2>Zmiany</h2>
<p>Hasła z obu źródeł zostały wybrane, połączone i na nowo sformatowane. Dodano angielskie formy odmienione, odsyłacze (np. <i>saw</i> → <i>see</i>) oraz listy czasowników frazowych.</p>
<p>Wersja z dnia {today}. Strona projektu: https://github.com/maciejkaniewski/kindle-en-pl-dictionary (kod źródłowy na licencji MIT).</p>
</body></html>
""")

    manifest = ['<item id="usage" href="usage.html" media-type="application/xhtml+xml"/>']
    spine = ['<itemref idref="usage"/>']
    for i, name in enumerate(files):
        manifest.append(f'<item id="c{i}" href="{name}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="c{i}"/>')
    manifest.append('<item id="copyright" href="copyright.html" media-type="application/xhtml+xml"/>')
    spine.append('<itemref idref="copyright"/>')
    manifest.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')

    nav = [("usage.html", "Jak korzystać ze słownika"), (files[0], "Słownik"), ("copyright.html", "Licencja i źródła")]
    points = "\n".join(
        f'  <navPoint id="n{i}" playOrder="{i + 1}"><navLabel><text>{esc(label)}</text></navLabel>'
        f'<content src="{href}"/></navPoint>' for i, (href, label) in enumerate(nav))
    with open(os.path.join(outdir, "toc.ncx"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="{esc(meta["identifier"])}"/></head>
<docTitle><text>{esc(title)}</text></docTitle>
<navMap>
{points}
</navMap>
</ncx>
""")

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{esc(title)}</dc:title>
    <dc:language>en</dc:language>
    <dc:creator>Wiktionary contributors</dc:creator>
    <dc:publisher>{esc(meta["publisher"])}</dc:publisher>
    <dc:rights>CC BY-SA 4.0</dc:rights>
    <dc:date>{today}</dc:date>
    <dc:identifier id="uid">{esc(meta["identifier"])}</dc:identifier>
    <x-metadata>
      <DictionaryInLanguage>en</DictionaryInLanguage>
      <DictionaryOutLanguage>pl</DictionaryOutLanguage>
      <DefaultLookupIndex>default</DefaultLookupIndex>
    </x-metadata>
  </metadata>
  <manifest>
    {chr(10).join("    " + m for m in manifest).strip()}
  </manifest>
  <spine toc="ncx">
    {chr(10).join("    " + s for s in spine).strip()}
  </spine>
  <guide>
    <reference type="index" title="Słownik" href="{files[0]}"/>
  </guide>
</package>
"""
    opf_path = os.path.join(outdir, "dictionary.opf")
    with open(opf_path, "w", encoding="utf-8") as f:
        f.write(opf)
    return opf_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("records", help="records JSONL from extract.py")
    ap.add_argument("--outdir", required=True, help="directory for the OPF/XHTML source")
    ap.add_argument("--title", default="Słownik angielsko-polski (Wiktionary)")
    ap.add_argument("--identifier", default="kindle-en-pl-dictionary")
    ap.add_argument("--publisher", default="kindle-en-pl-dictionary")
    ap.add_argument("--corrections", default=os.path.join(os.path.dirname(__file__), "..", "corrections", "polish.tsv"),
                    help="TSV of corrections; only rows with status 'approved' are applied")
    ap.add_argument("--kindling", help="path to kindling-cli; if given, compile the .mobi")
    ap.add_argument("-o", "--output", help="output .mobi path (with --kindling)")
    args = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir
    from corrections import load_approved
    corrections = load_approved(args.corrections)
    entries, lemma_forms, form_of_recs, used = load(args.records, corrections)
    stale = set(corrections) - used
    print(f"corrections applied: {len(used)}/{len(corrections)}", file=sys.stderr)
    for hw, original in sorted(stale):
        print(f"warning: stale correction (text no longer in source): {hw}: {original}", file=sys.stderr)
    final, phrasal_of, expr_of, collisions, by_lower = merge(entries, lemma_forms, form_of_recs)

    htmls = [render_entry(final[hw], final, phrasal_of, expr_of, by_lower)
             for hw in sorted(final, key=lambda h: (h.lower(), h))]
    meta = {"date": datetime.date.today().isoformat(), "identifier": args.identifier,
            "publisher": args.publisher}
    opf = write_package(args.outdir, args.title, htmls, meta)

    n_forms = sum(len(e.forms) for e in final.values())
    print(f"entries: {len(final)}  inflected forms: {n_forms}  collision/form entries: {collisions}  "
          f"base words with phrasal list: {len(phrasal_of)}", file=sys.stderr)
    print(f"source: {opf}", file=sys.stderr)

    stats = {
        "date": meta["date"],
        "entries": len(final),
        "inflected_forms": n_forms,
        "phrasal_verbs": sum(1 for e in final.values() if e.phrasal),
        "corrections_applied": len(used),
    }
    # next to the source dir, not inside it (kindling flags undeclared files)
    stats_path = os.path.join(os.path.dirname(os.path.abspath(args.outdir)), "stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        f.write("\n")

    if args.kindling:
        out = args.output or os.path.join(args.outdir, "dictionary.mobi")
        res = subprocess.run([args.kindling, "build", opf, "-o", out], capture_output=True, text=True)
        log = "\n".join(l for l in (res.stdout + res.stderr).splitlines() if "GLIBC" not in l)
        print(log[-3000:], file=sys.stderr)
        if res.returncode != 0:
            sys.exit(res.returncode)


if __name__ == "__main__":
    main()
