#!/usr/bin/env python3
"""Check relative Markdown links and images in a subject folder.

Usage: check_links.py [folder]   (default: current directory)

For every .md file (code fences and inline code are skipped):
- links and images to relative paths must point to an existing file;
- links to a .md file with an anchor (#Heading%20text) need a matching
  heading in that file (decoded text, case-insensitive); `#...` alone
  points into the same file;
- links to file.pdf#page=N need N within the PDF's page count; if the count
  is unknown or only approximate the link is reported as "unchecked".
http(s), mailto and other URL schemes are ignored.

Output: `file:line -> target: reason`. Exit code 1 if anything is broken.
Folders skipped: _templates (template copies left by skill versions before 1.1),
.prof-eng-work, .obsidian, .git and the source folders slides, exams, homework,
book.
"""
import os
import re
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slide_pages import page_count  # noqa: E402

SKIP_DIRS = {"_templates", ".prof-eng-work", ".obsidian", ".git", ".trash",
             "slides", "exams", "homework", "book"}
# a bare target may hold balanced parentheses: an anchor to the heading "R1 – Current (or voltage)"
LINK_RE = re.compile(r"(!?)\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\(\s*(<[^>]*>|(?:[^()\s]|\([^()\s]*\))+)"
                     r"(?:\s+\"[^\"]*\")?\s*\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def markdown_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.lower().endswith(".md"):
                yield os.path.join(dirpath, name)


def content_lines(path):
    """Yield (line number, text) outside code fences, inline code removed."""
    in_fence = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for number, line in enumerate(fh, 1):
            fence = FENCE_RE.match(line)
            if fence:
                if in_fence is None:
                    in_fence = fence.group(1)
                elif fence.group(1) == in_fence:
                    in_fence = None
                continue
            if in_fence is None:
                yield number, INLINE_CODE_RE.sub("", line.rstrip("\n"))


def anchor_key(text):
    """How a heading and a decoded link anchor are compared (md_to_tex.py uses it too)."""
    return text.strip().casefold()


_heading_cache = {}


def headings(path):
    if path not in _heading_cache:
        found = set()
        for _, line in content_lines(path):
            match = HEADING_RE.match(line)
            if match:
                found.add(anchor_key(match.group(2)))
        _heading_cache[path] = found
    return _heading_cache[path]


_page_cache = {}


def pdf_pages(path):
    if path not in _page_cache:
        _page_cache[path] = page_count(path)
    return _page_cache[path]


def check_target(source, target):
    """Return (status, reason) with status 'ok', 'broken' or 'unchecked'."""
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    path_part, _, anchor = target.partition("#")
    path_part = unquote(path_part)
    anchor = unquote(anchor)
    if path_part:
        resolved = os.path.normpath(os.path.join(os.path.dirname(source), path_part))
    else:
        resolved = source
    if not os.path.exists(resolved):
        return "broken", "missing file"
    if not anchor:
        return "ok", ""
    lower = resolved.lower()
    if lower.endswith(".pdf"):
        match = re.fullmatch(r"page=(\d+)", anchor.strip())
        if not match:
            return "ok", ""
        page = int(match.group(1))
        count, exact = pdf_pages(resolved)
        if count is None or not exact:
            return "unchecked", f"page {page}: page count unknown"
        if not 1 <= page <= count:
            return "broken", f"page {page} out of range (1-{count})"
        return "ok", ""
    if lower.endswith(".md"):
        known = headings(resolved)
        for part in anchor.split("#"):  # Obsidian allows #Heading#Subheading
            if part.strip() and anchor_key(part) not in known:
                return "broken", f"no heading '{part.strip()}'"
    return "ok", ""


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(root):
        print(f"error: not a folder: {root}", file=sys.stderr)
        return 2
    broken = unchecked = checked = 0
    for path in markdown_files(root):
        rel = os.path.relpath(path, root)
        for number, line in content_lines(path):
            for match in LINK_RE.finditer(line):
                target = match.group(3)
                if SCHEME_RE.match(target):
                    continue
                checked += 1
                status, reason = check_target(path, target)
                if status == "broken":
                    broken += 1
                    print(f"{rel}:{number} -> {target}: {reason}")
                elif status == "unchecked":
                    unchecked += 1
                    print(f"{rel}:{number} -> {target}: unchecked ({reason})")
    print(f"checked {checked} links: {broken} broken, {unchecked} unchecked")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
