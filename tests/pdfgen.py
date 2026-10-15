"""Write tiny synthetic PDFs (one or more lines of plain text per page).

Standard library only. Used by make_fixtures.py and the tests; the content is
always synthetic, never real course material.
"""
import os
import sys


def _escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path, pages, size=(595, 842)):
    """Write a PDF with one page per entry of `pages`.

    Each entry is a string (one line) or a list of strings (several lines).
    `size` is the page size in points (default A4 portrait).
    """
    width, height = size
    n = len(pages)
    # Object numbers: 1 catalog, 2 pages, 3 font, then (page, content) pairs.
    objects = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode()
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    for i, page in enumerate(pages):
        lines = [page] if isinstance(page, str) else list(page)
        ops = ["BT", "/F1 18 Tf", f"60 {height - 120} Td", "24 TL"]
        for line in lines:
            ops.append(f"({_escape(line)}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        page_no, content_no = 4 + 2 * i, 5 + 2 * i
        objects[page_no] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_no} 0 R >>"
        ).encode()
        objects[content_no] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objects[num] + b"\nendobj\n"
    xref_at = len(out)
    total = max(objects) + 1
    out += f"xref\n0 {total}\n0000000000 65535 f \n".encode()
    for num in range(1, total):
        out += f"{offsets[num]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {total} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(out)


if __name__ == "__main__":
    # Usage: pdfgen.py out.pdf N  -> N pages labelled "Page 1".."Page N"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    write_pdf(sys.argv[1], [f"Page {i}" for i in range(1, count + 1)])
