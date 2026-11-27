PYTHON   ?= python3 -I
KINDLING ?= bin/kindling-cli
PLWIKT   ?= data/raw/pl-extract.jsonl.gz
ENWIKT   ?= data/raw/kaikki-English.jsonl.gz

PILOT := build/pilot

.PHONY: all download pilot test-pilot clean

all: test-pilot

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

clean:
	rm -rf build
