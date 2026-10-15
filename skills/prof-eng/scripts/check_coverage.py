#!/usr/bin/env python3
"""Check that every slide of a lecture is covered by its note.

Usage: check_coverage.py [folder]   (default: current directory)

For every .md file whose frontmatter has `source` and `slides` (lecture
notes), parse the `## Slide coverage` table. Its first column holds single
slides or ranges ("3", "3-9", "3–9", "3, 5, 7-8"); rows whose second column
starts with "skipped" count as covered. Reports slides missing, slides listed
twice, slides beyond the slide count, and a mismatch between `slides` and the
PDF's page count when it can be determined. Exit code 1 on problems.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_links import markdown_files  # noqa: E402
from slide_pages import page_count  # noqa: E402

RANGE_RE = re.compile(r"^(\d+)\s*(?:[-–—]\s*(\d+))?$")


def frontmatter(lines):
    if not lines or lines[0].strip() != "---":
        return {}
    data = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        key, sep, value = line.partition(":")
        if sep and not key.startswith((" ", "\t")):
            value = re.sub(r"\s+#.*$", "", value).strip().strip("\"'")
            data[key.strip()] = value
    return {}


def coverage_rows(lines):
    """Yield (line number, first cell, second cell) of the coverage table."""
    inside = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.match(r"^##\s+Slide coverage\s*$", stripped, re.IGNORECASE):
            inside = True
            continue
        if inside and re.match(r"^#{1,2}\s", stripped):
            break
        if inside and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 2 or set(cells[0]) <= set("-: "):
                continue  # separator row
            if cells[0].lower() in ("slides", "slide"):
                continue  # header row
            yield number, cells[0], cells[1]


def parse_slides(cell):
    """'3–9, 12' -> [3..9, 12]; None if the cell is not a slide list."""
    slides = []
    for part in cell.split(","):
        match = RANGE_RE.match(part.strip())
        if not match:
            return None
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if end < start:
            return None
        slides.extend(range(start, end + 1))
    return slides


def check_note(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    meta = frontmatter(lines)
    if not meta.get("source") or not meta.get("slides"):
        return None  # not a lecture note
    problems = []
    try:
        total = int(meta["slides"])
    except ValueError:
        return [f"frontmatter 'slides' is not a number: {meta['slides']}"]

    pdf = os.path.normpath(os.path.join(os.path.dirname(path), meta["source"]))
    if os.path.exists(pdf):
        count, exact = page_count(pdf)
        if exact and count != total:
            problems.append(f"frontmatter says {total} slides, {meta['source']} has {count} pages")

    seen = {}
    rows = list(coverage_rows(lines))
    if not rows:
        return problems + ["no '## Slide coverage' table"]
    for number, first, _second in rows:
        slides = parse_slides(first)
        if slides is None:
            problems.append(f"line {number}: cannot read slides '{first}'")
            continue
        for slide in slides:
            if slide in seen:
                problems.append(f"slide {slide} listed twice (lines {seen[slide]} and {number})")
            else:
                seen[slide] = number
            if slide > total or slide < 1:
                problems.append(f"line {number}: slide {slide} outside 1-{total}")
    missing = [s for s in range(1, total + 1) if s not in seen]
    if missing:
        problems.append("slides missing: " + compress(missing))
    return problems


def compress(numbers):
    """[1,2,3,7] -> '1-3, 7'."""
    out, start, prev = [], None, None
    for n in numbers:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append(f"{start}-{prev}" if prev > start else str(start))
            start = prev = n
    if start is not None:
        out.append(f"{start}-{prev}" if prev > start else str(start))
    return ", ".join(out)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(root):
        print(f"error: not a folder: {root}", file=sys.stderr)
        return 2
    notes = bad = 0
    for path in markdown_files(root):
        problems = check_note(path)
        if problems is None:
            continue
        notes += 1
        rel = os.path.relpath(path, root)
        if problems:
            bad += 1
            for problem in problems:
                print(f"{rel}: {problem}")
    print(f"checked {notes} notes: {bad} with problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
