#!/usr/bin/env python3
"""Convert bib.bib to publications.yaml for Hugo."""

import re
import yaml
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

CATEGORY_ORDER = ["conference", "journal", "book_chapter", "patent", "thesis"]

CATEGORY_LABELS = {
    "conference": "Conference Papers",
    "journal": "Journal Articles",
    "book_chapter": "Book Chapters",
    "patent": "Patents",
    "thesis": "Thesis",
}

SKIP_KEYS = {
    # Duplicate arXiv shadow entries and other noise
    "siuphysical",           # no year, no venue
    "shaib2403standardizing", # arXiv URL-only citation
    "wang2308knowledge",      # arXiv URL-only citation
}


def format_authors(raw):
    """Convert 'Last, First and Last, First' to 'First Last, First Last'."""
    parts = [p.strip() for p in raw.split(" and ")]
    formatted = []
    for p in parts:
        if "," in p:
            last, first = p.split(",", 1)
            formatted.append(f"{first.strip()} {last.strip()}")
        else:
            formatted.append(p)
    return ", ".join(formatted)


def clean(s):
    """Remove BibTeX braces and normalize whitespace."""
    s = re.sub(r"[{}]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def categorize(entry):
    etype = entry["ENTRYTYPE"].lower()
    note = clean(entry.get("note", "")).lower()

    if "patent" in note:
        return "patent"
    if etype == "phdthesis":
        return "thesis"
    if etype == "incollection":
        return "book_chapter"
    if etype == "inproceedings":
        return "conference"
    if etype == "article":
        journal = clean(entry.get("journal", "")).lower()
        if "arxiv" in journal:
            return None  # skip preprints
        return "journal"
    return None  # skip @misc non-patents, etc.


def entry_to_dict(entry):
    title = clean(entry.get("title", ""))
    authors = format_authors(clean(entry.get("author", "")))
    year = clean(entry.get("year", ""))

    # Build venue string
    venue = (
        clean(entry.get("booktitle", ""))
        or clean(entry.get("journal", ""))
        or clean(entry.get("school", ""))
        or ""
    )

    note = clean(entry.get("note", ""))
    url = clean(entry.get("url", ""))

    return {
        "title": title,
        "authors": authors,
        "venue": venue,
        "year": int(year) if year.isdigit() else year,
        "note": note if note else None,
        "url": url if url else None,
    }


def main():
    with open("bib.bib", encoding="utf-8") as f:
        raw = f.read()

    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    db = bibtexparser.loads(raw, parser=parser)

    seen_keys = set()
    by_category = {c: [] for c in CATEGORY_ORDER}

    for entry in db.entries:
        key = entry.get("ID", "")
        if key in SKIP_KEYS or key in seen_keys:
            continue
        seen_keys.add(key)

        cat = categorize(entry)
        if cat is None:
            continue

        by_category[cat].append(entry_to_dict(entry))

    # Sort each category newest first
    for cat in by_category:
        by_category[cat].sort(key=lambda e: e["year"] if isinstance(e["year"], int) else 0, reverse=True)

    # Build output structure
    output = []
    for cat in CATEGORY_ORDER:
        entries = by_category[cat]
        if entries:
            # Remove None values from each entry dict
            cleaned = [{k: v for k, v in e.items() if v is not None} for e in entries]
            output.append({
                "category": cat,
                "label": CATEGORY_LABELS[cat],
                "entries": cleaned,
            })

    with open("publications.yaml", "w", encoding="utf-8") as f:
        yaml.dump(output, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    total = sum(len(s["entries"]) for s in output)
    for section in output:
        print(f"  {section['label']}: {len(section['entries'])}")
    print(f"  Total: {total}")


if __name__ == "__main__":
    main()
