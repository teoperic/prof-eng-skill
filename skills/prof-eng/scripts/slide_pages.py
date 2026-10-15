#!/usr/bin/env python3
"""Page count, read chunks and short hash of a PDF.

Usage: slide_pages.py <pdf> [--chunk N]

Output (one item per line):
    pages: 42                  ("pages: 42 (approximate)" if only estimated)
    chunks: 1-15 16-30 31-42
    sha256: 3f9a0c12be47

Page count: pypdf if installed, then `pdfinfo` (poppler), then counting
`/Type /Page` objects in the file (approximate). Standard library only.
"""
import argparse
import hashlib
import re
import shutil
import subprocess
import sys


def page_count(path):
    """Return (count, exact). count is None if it cannot be determined."""
    try:
        from pypdf import PdfReader  # optional dependency

        return len(PdfReader(path).pages), True
    except Exception:
        pass
    if shutil.which("pdfinfo"):
        try:
            out = subprocess.run(
                ["pdfinfo", path], capture_output=True, text=True, timeout=60
            ).stdout
            match = re.search(r"^Pages:\s+(\d+)", out, re.MULTILINE)
            if match:
                return int(match.group(1)), True
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None, False
    count = len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data))
    return (count or None), False


def chunks(count, size):
    """Ranges like ['1-15', '16-30', '31-42'] covering pages 1..count."""
    out = []
    for start in range(1, count + 1, size):
        end = min(start + size - 1, count)
        out.append(f"{start}-{end}" if end > start else str(start))
    return out


def short_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:12]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pdf")
    parser.add_argument("--chunk", type=int, default=15, help="pages per chunk (default 15)")
    args = parser.parse_args()
    if args.chunk < 1:
        parser.error("--chunk must be at least 1")
    try:
        digest = short_hash(args.pdf)
    except OSError as err:
        print(f"error: cannot read {args.pdf}: {err}", file=sys.stderr)
        return 1
    count, exact = page_count(args.pdf)
    if count is None:
        print("pages: unknown")
        print("chunks: unknown")
    else:
        print(f"pages: {count}" + ("" if exact else " (approximate)"))
        print("chunks: " + " ".join(chunks(count, args.chunk)))
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
