PYTHON   ?= python3 -I
KINDLING ?= bin/kindling-cli
PLWIKT   ?= data/raw/pl-extract.jsonl.gz
# English Wiktionary: raw wiktextract dump (all languages; English entries are filtered).
# The smaller kaikki-English.jsonl.gz extract also works but is deprecated upstream.
ENWIKT   ?= data/raw/raw-wiktextract-data.jsonl.gz

PILOT := build/pilot
FULL  := build/full

.PHONY: all download pilot test-pilot full test clean

all: test

download:
	tools/download.sh

$(PILOT)/records.jsonl: pilot/words.txt tools/extract.py $(PLWIKT) $(ENWIKT)
	@mkdir -p $(PILOT)
	$(PYTHON) tools/extract.py --plwikt $(PLWIKT) --enwikt $(ENWIKT) --words pilot/words.txt -o $@

$(PILOT)/en-pl-pilot.mobi: $(PILOT)/records.jsonl tools/build.py
	$(PYTHON) tools/build.py $< --outdir $(PILOT)/src \
	  --title "Słownik angielsko-polski (Wiktionary) – PILOT" \
	  --identifier kindle-en-pl-dictionary-pilot \
	  --kindling $(KINDLING) -o $@

pilot: $(PILOT)/en-pl-pilot.mobi

test-pilot: pilot
	$(PYTHON) tools/check_lookups.py $(PILOT)/en-pl-pilot.mobi tests/lookups_pilot.tsv --kindling $(KINDLING)

$(FULL)/records.jsonl: tools/extract.py $(PLWIKT) $(ENWIKT)
	@mkdir -p $(FULL)
	$(PYTHON) tools/extract.py --plwikt $(PLWIKT) --enwikt $(ENWIKT) -o $@

$(FULL)/kindle-en-pl-dictionary.mobi: $(FULL)/records.jsonl tools/build.py
	$(PYTHON) tools/build.py $< --outdir $(FULL)/src \
	  --title "Słownik angielsko-polski (Wiktionary)" \
	  --kindling $(KINDLING) -o $@

full: $(FULL)/kindle-en-pl-dictionary.mobi

test: full
	$(PYTHON) tools/check_lookups.py $(FULL)/kindle-en-pl-dictionary.mobi tests/lookups.tsv \
	  --src $(FULL)/src --kindling $(KINDLING)

clean:
	rm -rf build
