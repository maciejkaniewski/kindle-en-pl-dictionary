PYTHON   ?= python3 -I
KINDLING ?= bin/kindling-cli
PLWIKT   ?= data/raw/pl-extract.jsonl.gz
# English Wiktionary: raw wiktextract dump (all languages; English entries are filtered).
# The smaller kaikki-English.jsonl.gz extract also works but is deprecated upstream.
ENWIKT   ?= data/raw/raw-wiktextract-data.jsonl.gz

# Shown in the dictionary title on the Kindle; CI sets it to the release tag (e.g. v0.1.1).
DICT_VERSION ?= dev

PILOT := build/pilot
FULL  := build/full

.PHONY: all download pilot test-pilot full test test-book clean FORCE

all: test

download:
	tools/download.sh

$(PILOT)/records.jsonl: pilot/words.txt tools/extract.py $(PLWIKT) $(ENWIKT)
	@mkdir -p $(PILOT)
	$(PYTHON) tools/extract.py --plwikt $(PLWIKT) --enwikt $(ENWIKT) --words pilot/words.txt -o $@

$(PILOT)/en-pl-pilot.mobi: $(PILOT)/records.jsonl tools/build.py tools/corrections.py corrections/polish.tsv
	$(PYTHON) tools/build.py $< --outdir $(PILOT)/src \
	  --title "Słownik angielsko-polski (frazy i idiomy) – PILOT" \
	  --identifier kindle-en-pl-dictionary-pilot \
	  --kindling $(KINDLING) -o $@

pilot: $(PILOT)/en-pl-pilot.mobi

test-pilot: pilot
	$(PYTHON) tools/check_lookups.py $(PILOT)/en-pl-pilot.mobi tests/lookups_pilot.tsv --kindling $(KINDLING)

$(FULL)/records.jsonl: tools/extract.py $(PLWIKT) $(ENWIKT)
	@mkdir -p $(FULL)
	$(PYTHON) tools/extract.py --plwikt $(PLWIKT) --enwikt $(ENWIKT) -o $@

$(FULL)/version: FORCE
	@mkdir -p $(FULL)
	@echo '$(DICT_VERSION)' | cmp -s - $@ || echo '$(DICT_VERSION)' > $@

$(FULL)/kindle-en-pl-dictionary.mobi: $(FULL)/records.jsonl $(FULL)/version tools/build.py tools/corrections.py corrections/polish.tsv
	$(PYTHON) tools/build.py $< --outdir $(FULL)/src \
	  --version $(DICT_VERSION) \
	  --kindling $(KINDLING) -o $@

full: $(FULL)/kindle-en-pl-dictionary.mobi

test: full
	$(PYTHON) tools/check_lookups.py $(FULL)/kindle-en-pl-dictionary.mobi tests/lookups.tsv \
	  --src $(FULL)/src --kindling $(KINDLING)

clean:
	rm -rf build

# Small English test book for checking lookups on a real Kindle
# (copy it to documents/ on the device, next to the dictionary in documents/dictionaries/).
build/device/dictionary-test.azw3: tests/device/dictionary-test.opf tests/device/dictionary-test.html tests/device/toc.ncx
	@mkdir -p build/device
	$(KINDLING) build tests/device/dictionary-test.opf -o $@ --no-validate  # a test book needs no cover

test-book: build/device/dictionary-test.azw3
