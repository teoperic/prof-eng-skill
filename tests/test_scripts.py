"""Tests for the helper scripts in skills/prof-eng/scripts/.

Run from the repo root: python3 -m unittest discover tests
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "skills", "prof-eng", "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)

from make_fixtures import make_subject  # noqa: E402
from pdfgen import write_pdf  # noqa: E402
import slide_pages  # noqa: E402


def run(script, *args):
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script), *args],
        capture_output=True, text=True, timeout=120,
    )


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(text).lstrip("\n"))


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prof-eng-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp)


class SlidePagesTest(TempDirTest):
    def test_chunk_ranges(self):
        self.assertEqual(slide_pages.chunks(42, 15), ["1-15", "16-30", "31-42"])
        self.assertEqual(slide_pages.chunks(15, 15), ["1-15"])
        self.assertEqual(slide_pages.chunks(16, 15), ["1-15", "16"])
        self.assertEqual(slide_pages.chunks(5, 2), ["1-2", "3-4", "5"])

    def test_output_and_hash(self):
        pdf = os.path.join(self.tmp, "x.pdf")
        write_pdf(pdf, [f"Page {i}" for i in range(1, 33)])
        result = run("slide_pages.py", pdf)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertTrue(lines[0].startswith("pages: 32"), lines)
        self.assertEqual(lines[1], "chunks: 1-15 16-30 31-32")
        with open(pdf, "rb") as fh:
            expected = hashlib.sha256(fh.read()).hexdigest()[:12]
        self.assertEqual(lines[2], f"sha256: {expected}")

    def test_custom_chunk(self):
        pdf = os.path.join(self.tmp, "x.pdf")
        write_pdf(pdf, ["a", "b", "c", "d", "e"])
        result = run("slide_pages.py", pdf, "--chunk", "2")
        self.assertIn("chunks: 1-2 3-4 5", result.stdout)

    def test_fallback_count_without_tools(self):
        pdf = os.path.join(self.tmp, "x.pdf")
        write_pdf(pdf, ["a", "b", "c"])
        # The raw object count is the last fallback; it must not count /Pages.
        with open(pdf, "rb") as fh:
            data = fh.read()
        import re
        self.assertEqual(len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data)), 3)

    def test_approximate_without_tools(self):
        pdf = os.path.join(self.tmp, "x.pdf")
        write_pdf(pdf, ["a", "b", "c"])
        blocker = os.path.join(self.tmp, "block")
        write(os.path.join(blocker, "pypdf.py"), "raise ImportError('blocked')\n")
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "slide_pages.py"), pdf],
            capture_output=True, text=True, env={"PATH": "", "PYTHONPATH": blocker}, timeout=60,
        )
        self.assertIn("pages: 3 (approximate)", result.stdout)

    def test_missing_file(self):
        result = run("slide_pages.py", os.path.join(self.tmp, "nope.pdf"))
        self.assertEqual(result.returncode, 1)


class RenderPageTest(TempDirTest):
    def test_render(self):
        pdf = os.path.join(self.tmp, "x.pdf")
        write_pdf(pdf, ["Page 1", "Page 2"])
        out = os.path.join(self.tmp, "img", "x-p2.png")
        result = run("render_page.py", pdf, "2", out, "--dpi", "50")
        if result.returncode == 2:
            self.skipTest("no PDF renderer installed (pdftoppm or PyMuPDF)")
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(out, "rb") as fh:
            self.assertEqual(fh.read(8), b"\x89PNG\r\n\x1a\n")

    def test_bad_page(self):
        pdf = os.path.join(self.tmp, "x.pdf")
        write_pdf(pdf, ["Page 1"])
        result = run("render_page.py", pdf, "5", os.path.join(self.tmp, "o.png"))
        if result.returncode == 2:
            self.skipTest("no PDF renderer installed (pdftoppm or PyMuPDF)")
        self.assertEqual(result.returncode, 1)

    def test_no_renderer_exits_2(self):
        # Hide pdftoppm and PyMuPDF: empty PATH and a Python that cannot import fitz.
        pdf = os.path.join(self.tmp, "x.pdf")
        write_pdf(pdf, ["Page 1"])
        blocker = os.path.join(self.tmp, "block")
        write(os.path.join(blocker, "fitz.py"), "raise ImportError('blocked')\n")
        env = {"PATH": "", "PYTHONPATH": blocker}
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "render_page.py"), pdf, "1",
             os.path.join(self.tmp, "o.png")],
            capture_output=True, text=True, env=env, timeout=60,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("no PDF renderer", result.stderr)


class CheckLinksTest(TempDirTest):
    def make_folder(self):
        root = self.tmp
        write_pdf(os.path.join(root, "slides", "L01.pdf"), ["s1", "s2", "s3"])
        os.makedirs(os.path.join(root, "notes", "img"))
        with open(os.path.join(root, "notes", "img", "L01-s2.png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")
        write(os.path.join(root, "notes", "L01-intro.md"), """
            # L01 – Intro
            ## Core content
            ### 2. Partial fractions
            Text.
        """)
        return root

    def check(self, body):
        root = self.make_folder()
        write(os.path.join(root, "cheatsheets", "L01-cheatsheet.md"), body)
        result = run("check_links.py", root)
        return result.returncode, result.stdout

    def test_good_links(self):
        code, out = self.check("""
            [note](../notes/L01-intro.md)
            [section](../notes/L01-intro.md#2.%20Partial%20fractions)
            [case](../notes/L01-intro.md#2.%20partial%20FRACTIONS)
            [slide 3](../slides/L01.pdf#page=3)
            ![Slide 2](../notes/img/L01-s2.png)
            [web](https://example.com) [mail](mailto:a@b.c)
            ## Local
            [here](#Local)
        """)
        self.assertEqual(code, 0, out)
        self.assertIn("0 broken", out)

    def test_missing_file(self):
        code, out = self.check("[gone](../notes/L09-missing.md)\n")
        self.assertEqual(code, 1)
        self.assertIn("L01-cheatsheet.md:1 -> ../notes/L09-missing.md: missing file", out)

    def test_missing_anchor(self):
        code, out = self.check("[x](../notes/L01-intro.md#Laplace%20table)\n")
        self.assertEqual(code, 1)
        self.assertIn("no heading 'Laplace table'", out)

    def test_bad_page(self):
        code, out = self.check("[slide 9](../slides/L01.pdf#page=9)\n")
        self.assertEqual(code, 1)
        self.assertIn("page 9 out of range (1-3)", out)

    def test_missing_image(self):
        code, out = self.check("![Slide 7](../notes/img/L01-s7.png)\n")
        self.assertEqual(code, 1)
        self.assertIn("missing file", out)

    def test_code_fence_and_inline_code_ignored(self):
        code, out = self.check("""
            ```markdown
            [broken](nowhere.md)
            ```
            Inline: `[also broken](nowhere.md)`
        """)
        self.assertEqual(code, 0, out)
        self.assertIn("checked 0 links", out)

    def test_templates_folder_skipped(self):
        root = self.make_folder()
        write(os.path.join(root, "_templates", "lecture-note.md"), "[x](../slides/<file>.pdf#page=3)\n")
        result = run("check_links.py", root)
        self.assertEqual(result.returncode, 0, result.stdout)


class CheckCoverageTest(TempDirTest):
    def note(self, rows, slides=6, pages=6):
        root = self.tmp
        write_pdf(os.path.join(root, "slides", "L01.pdf"), [f"s{i}" for i in range(1, pages + 1)])
        table = "\n".join(rows)
        text = textwrap.dedent(f"""
            ---
            lecture: 1
            source: ../slides/L01.pdf
            slides: {slides}
            status: draft        # draft | reviewed
            ---
            # L01 – Intro
            ## Slide coverage
            | Slides | Section |
            |---|---|
            {{table}}

            ## After
            | 99 | not part of the table |
        """).replace("{table}", table)
        write(os.path.join(root, "notes", "L01-intro.md"), text)
        result = run("check_coverage.py", root)
        return result.returncode, result.stdout

    def test_full(self):
        code, out = self.note(["| 1 | skipped (title) |", "| 2–4 | 1. Topic |", "| 5, 6 | 2. Topic |"])
        self.assertEqual(code, 0, out)
        self.assertIn("checked 1 notes: 0 with problems", out)

    def test_gap(self):
        code, out = self.note(["| 1 | skipped (title) |", "| 2-3 | 1. Topic |", "| 6 | 2. Topic |"])
        self.assertEqual(code, 1)
        self.assertIn("slides missing: 4-5", out)

    def test_overlap(self):
        code, out = self.note(["| 1-4 | 1. Topic |", "| 4-6 | 2. Topic |"])
        self.assertEqual(code, 1)
        self.assertIn("slide 4 listed twice", out)

    def test_skipped_rows_count(self):
        code, out = self.note(["| 1 | skipped (title) |", "| 2-5 | 1. Topic |", "| 6 | skipped (thank-you) |"])
        self.assertEqual(code, 0, out)

    def test_page_count_mismatch(self):
        code, out = self.note(["| 1-6 | 1. Topic |"], slides=6, pages=8)
        self.assertEqual(code, 1)
        self.assertIn("has 8 pages", out)

    def test_solution_files_ignored(self):
        write(os.path.join(self.tmp, "solutions", "exam-x.md"), """
            ---
            exam: x
            source: ../exams/x.pdf
            ---
            # Exam x
        """)
        result = run("check_coverage.py", self.tmp)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("checked 0 notes", result.stdout)


class FixturesTest(TempDirTest):
    def test_fixture_folder(self):
        root = make_subject(self.tmp)
        exams = sorted(os.listdir(os.path.join(root, "exams")))
        self.assertEqual(exams, ["2023-jan-solution.pdf", "2023-jan.pdf"])
        self.assertEqual(len(os.listdir(os.path.join(root, "book"))), 1)
        count, _ = slide_pages.page_count(os.path.join(root, "slides", "L01-ohms-law.pdf"))
        self.assertEqual(count, 6)


if __name__ == "__main__":
    unittest.main()
