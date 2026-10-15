#!/usr/bin/env python3
"""Render one PDF page to a PNG file.

Usage: render_page.py <pdf> <page> <out.png> [--dpi 150]

Tries `pdftoppm` (poppler) first, then PyMuPDF (`fitz`) if installed.
Exit codes: 0 rendered, 1 rendering failed (bad file or page),
2 no renderer available (the caller falls back to description plus link).
"""
import argparse
import os
import shutil
import subprocess
import sys


def render_pdftoppm(pdf, page, out, dpi):
    stem = out[:-4] if out.lower().endswith(".png") else out
    result = subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
         "-singlefile", pdf, stem],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0 or not os.path.exists(stem + ".png"):
        raise RuntimeError(result.stderr.strip() or "pdftoppm produced no file")
    if stem + ".png" != out:
        os.replace(stem + ".png", out)


def render_fitz(fitz, pdf, page, out, dpi):
    doc = fitz.open(pdf)
    try:
        if not 1 <= page <= doc.page_count:
            raise RuntimeError(f"page {page} out of range (1-{doc.page_count})")
        doc[page - 1].get_pixmap(dpi=dpi).save(out)
    finally:
        doc.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pdf")
    parser.add_argument("page", type=int)
    parser.add_argument("out")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()
    if not os.path.isfile(args.pdf):
        print(f"error: no such file: {args.pdf}", file=sys.stderr)
        return 1
    if args.page < 1:
        print("error: page numbers start at 1", file=sys.stderr)
        return 1
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    tried = False
    if shutil.which("pdftoppm"):
        tried = True
        try:
            render_pdftoppm(args.pdf, args.page, args.out, args.dpi)
            print(f"rendered {args.pdf} page {args.page} -> {args.out} (pdftoppm, {args.dpi} dpi)")
            return 0
        except (RuntimeError, OSError, subprocess.SubprocessError) as err:
            print(f"pdftoppm failed: {err}", file=sys.stderr)
    try:
        import fitz  # PyMuPDF, optional
    except ImportError:
        fitz = None
    if fitz is not None:
        tried = True
        try:
            render_fitz(fitz, args.pdf, args.page, args.out, args.dpi)
            print(f"rendered {args.pdf} page {args.page} -> {args.out} (PyMuPDF, {args.dpi} dpi)")
            return 0
        except Exception as err:  # PyMuPDF raises its own error types
            print(f"PyMuPDF failed: {err}", file=sys.stderr)
    if not tried:
        print(
            "no PDF renderer available: install poppler (pdftoppm) or PyMuPDF "
            "(pip install pymupdf). Keep the figure description and page link only.",
            file=sys.stderr,
        )
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
